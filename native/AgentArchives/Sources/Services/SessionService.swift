import Foundation

actor SessionService {
    private let claudeBasePath: URL
    private let openCodeBasePath: URL
    private let fileManager = FileManager.default
    private let decoder: JSONDecoder
    
    init() {
        let home = fileManager.homeDirectoryForCurrentUser
        claudeBasePath = home.appendingPathComponent(".claude/projects")
        openCodeBasePath = home.appendingPathComponent(".local/share/opencode/sessions")
        
        decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
    }
    
    func loadSessions(for agent: AgentType) async throws -> [Session] {
        switch agent {
        case .claude:
            return try await loadClaudeSessions()
        case .opencode:
            return try await loadOpenCodeSessions()
        }
    }
    
    private func loadClaudeSessions() async throws -> [Session] {
        var sessions: [Session] = []
        
        guard fileManager.fileExists(atPath: claudeBasePath.path) else {
            return sessions
        }
        
        let projectDirs = try fileManager.contentsOfDirectory(
            at: claudeBasePath,
            includingPropertiesForKeys: [.isDirectoryKey],
            options: [.skipsHiddenFiles]
        )
        
        for projectDir in projectDirs {
            var isDir: ObjCBool = false
            guard fileManager.fileExists(atPath: projectDir.path, isDirectory: &isDir),
                  isDir.boolValue else { continue }
            
            let sessionFiles = try fileManager.contentsOfDirectory(
                at: projectDir,
                includingPropertiesForKeys: [.contentModificationDateKey],
                options: [.skipsHiddenFiles]
            ).filter { $0.pathExtension == "json" }
            
            for sessionFile in sessionFiles {
                if let session = try? await parseClaudeSession(at: sessionFile, project: projectDir.lastPathComponent) {
                    sessions.append(session)
                }
            }
        }
        
        return sessions.sorted { $0.lastActivity > $1.lastActivity }
    }
    
    private func parseClaudeSession(at url: URL, project: String) async throws -> Session {
        let data = try Data(contentsOf: url)
        let conversation = try decoder.decode(ConversationData.self, from: data)
        
        let sessionId = url.deletingPathExtension().lastPathComponent
        let messages = conversation.messages
        
        var preview = ""
        var firstTimestamp: Date?
        var lastTimestamp: Date?
        
        for msg in messages {
            if let content = msg.message?.content?.textContent, !content.isEmpty {
                if preview.isEmpty {
                    preview = String(content.prefix(100))
                }
            }
            
            if let ts = msg.timestamp, let date = ISO8601DateFormatter().date(from: ts) {
                if firstTimestamp == nil { firstTimestamp = date }
                lastTimestamp = date
            }
        }
        
        return Session(
            id: sessionId,
            title: preview,
            project: project,
            preview: preview,
            messageCount: messages.count,
            lastActivity: lastTimestamp ?? Date(),
            firstTimestamp: firstTimestamp,
            projectFolder: project,
            fileName: url.lastPathComponent
        )
    }
    
    private func loadOpenCodeSessions() async throws -> [Session] {
        var sessions: [Session] = []
        
        guard fileManager.fileExists(atPath: openCodeBasePath.path) else {
            return sessions
        }
        
        let sessionDirs = try fileManager.contentsOfDirectory(
            at: openCodeBasePath,
            includingPropertiesForKeys: [.isDirectoryKey],
            options: [.skipsHiddenFiles]
        )
        
        for sessionDir in sessionDirs {
            let messagesFile = sessionDir.appendingPathComponent("messages.json")
            let sessionFile = sessionDir.appendingPathComponent("session.json")
            
            guard fileManager.fileExists(atPath: messagesFile.path) else { continue }
            
            if let session = try? await parseOpenCodeSession(
                sessionDir: sessionDir,
                messagesFile: messagesFile,
                sessionFile: sessionFile
            ) {
                sessions.append(session)
            }
        }
        
        return sessions.sorted { $0.lastActivity > $1.lastActivity }
    }
    
    private func parseOpenCodeSession(sessionDir: URL, messagesFile: URL, sessionFile: URL) async throws -> Session {
        let sessionId = sessionDir.lastPathComponent
        
        var title = ""
        var project = ""
        
        if fileManager.fileExists(atPath: sessionFile.path) {
            let data = try Data(contentsOf: sessionFile)
            if let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
                title = json["title"] as? String ?? ""
                project = json["working_directory"] as? String ?? ""
            }
        }
        
        let messagesData = try Data(contentsOf: messagesFile)
        let messageCount: Int
        if let json = try? JSONSerialization.jsonObject(with: messagesData) as? [[String: Any]] {
            messageCount = json.count
        } else {
            messageCount = 0
        }
        
        let attributes = try fileManager.attributesOfItem(atPath: messagesFile.path)
        let lastModified = attributes[.modificationDate] as? Date ?? Date()
        
        return Session(
            id: sessionId,
            title: title,
            project: project,
            preview: title.isEmpty ? "OpenCode Session" : title,
            messageCount: messageCount,
            lastActivity: lastModified
        )
    }
    
    func loadMessages(for session: Session, agent: AgentType) async throws -> [Message] {
        switch agent {
        case .claude:
            return try await loadClaudeMessages(for: session)
        case .opencode:
            return try await loadOpenCodeMessages(for: session)
        }
    }
    
    private func loadClaudeMessages(for session: Session) async throws -> [Message] {
        guard let projectFolder = session.projectFolder,
              let fileName = session.fileName else { return [] }
        
        let url = claudeBasePath
            .appendingPathComponent(projectFolder)
            .appendingPathComponent(fileName)
        
        let data = try Data(contentsOf: url)
        let conversation = try decoder.decode(ConversationData.self, from: data)
        
        return conversation.messages.compactMap { raw -> Message? in
            guard let role = raw.message?.role,
                  let content = raw.message?.content?.textContent,
                  !content.isEmpty else { return nil }
            
            let timestamp: Date?
            if let ts = raw.timestamp {
                timestamp = ISO8601DateFormatter().date(from: ts)
            } else {
                timestamp = nil
            }
            
            return Message(
                role: role == "user" ? .user : .assistant,
                content: content,
                timestamp: timestamp
            )
        }
    }
    
    private func loadOpenCodeMessages(for session: Session) async throws -> [Message] {
        let url = openCodeBasePath
            .appendingPathComponent(session.id)
            .appendingPathComponent("messages.json")
        
        let data = try Data(contentsOf: url)
        guard let json = try? JSONSerialization.jsonObject(with: data) as? [[String: Any]] else {
            return []
        }
        
        return json.compactMap { item -> Message? in
            guard let role = item["role"] as? String,
                  let content = item["content"] as? String else { return nil }
            
            return Message(
                role: role == "user" ? .user : .assistant,
                content: content
            )
        }
    }
}
