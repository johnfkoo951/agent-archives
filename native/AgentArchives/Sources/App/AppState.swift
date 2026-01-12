import SwiftUI
import Observation

enum AppTab: String, CaseIterable {
    case sessions
    case dashboard
    case monitor
}

enum AgentType: String, CaseIterable {
    case claude = "Claude Code"
    case opencode = "OpenCode"
}

@Observable
final class AppState {
    var sessions: [Session] = []
    var filteredSessions: [Session] = []
    var selectedSession: Session?
    var selectedTab: AppTab = .sessions
    var selectedAgent: AgentType = .claude
    
    var searchText: String = "" {
        didSet { filterSessions() }
    }
    var isSearchFocused: Bool = false
    var isLoading: Bool = false
    var errorMessage: String?
    
    var sessionNames: [String: String] = [:]
    var sessionTags: [String: [String]] = [:]
    var allTags: [String] = []
    var selectedTag: String?
    
    private let sessionService = SessionService()
    private let dataURL: URL
    
    init() {
        let appSupport = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first!
        let appDir = appSupport.appendingPathComponent("AgentArchives")
        try? FileManager.default.createDirectory(at: appDir, withIntermediateDirectories: true)
        dataURL = appDir
        
        loadUserData()
        Task { await loadSessions() }
    }
    
    @MainActor
    func loadSessions() async {
        isLoading = true
        errorMessage = nil
        
        do {
            sessions = try await sessionService.loadSessions(for: selectedAgent)
            filterSessions()
        } catch {
            errorMessage = error.localizedDescription
        }
        
        isLoading = false
    }
    
    func filterSessions() {
        var result = sessions
        
        if let tag = selectedTag {
            result = result.filter { sessionTags[$0.id]?.contains(tag) == true }
        }
        
        if !searchText.isEmpty {
            let query = searchText.lowercased()
            result = result.filter { session in
                session.title.lowercased().contains(query) ||
                session.project.lowercased().contains(query) ||
                session.preview.lowercased().contains(query) ||
                (sessionNames[session.id]?.lowercased().contains(query) == true)
            }
        }
        
        filteredSessions = result
    }
    
    func switchAgent(_ agent: AgentType) {
        selectedAgent = agent
        selectedSession = nil
        selectedTag = nil
        Task { await loadSessions() }
    }
    
    func getDisplayName(for session: Session) -> String {
        sessionNames[session.id] ?? session.displayTitle
    }
    
    func setSessionName(_ name: String, for sessionId: String) {
        if name.isEmpty {
            sessionNames.removeValue(forKey: sessionId)
        } else {
            sessionNames[sessionId] = name
        }
        saveUserData()
    }
    
    func getTags(for sessionId: String) -> [String] {
        sessionTags[sessionId] ?? []
    }
    
    func addTag(_ tag: String, to sessionId: String) {
        var tags = sessionTags[sessionId] ?? []
        if !tags.contains(tag) {
            tags.append(tag)
            sessionTags[sessionId] = tags
            updateAllTags()
            saveUserData()
        }
    }
    
    func removeTag(_ tag: String, from sessionId: String) {
        var tags = sessionTags[sessionId] ?? []
        tags.removeAll { $0 == tag }
        sessionTags[sessionId] = tags.isEmpty ? nil : tags
        updateAllTags()
        saveUserData()
    }
    
    private func updateAllTags() {
        var tags = Set<String>()
        for tagList in sessionTags.values {
            tags.formUnion(tagList)
        }
        allTags = Array(tags).sorted()
    }
    
    private func loadUserData() {
        let namesURL = dataURL.appendingPathComponent("session-names.json")
        let tagsURL = dataURL.appendingPathComponent("session-tags.json")
        
        if let data = try? Data(contentsOf: namesURL),
           let dict = try? JSONDecoder().decode([String: String].self, from: data) {
            sessionNames = dict
        }
        
        if let data = try? Data(contentsOf: tagsURL),
           let dict = try? JSONDecoder().decode([String: [String]].self, from: data) {
            sessionTags = dict
            updateAllTags()
        }
    }
    
    private func saveUserData() {
        let namesURL = dataURL.appendingPathComponent("session-names.json")
        let tagsURL = dataURL.appendingPathComponent("session-tags.json")
        
        if let data = try? JSONEncoder().encode(sessionNames) {
            try? data.write(to: namesURL)
        }
        if let data = try? JSONEncoder().encode(sessionTags) {
            try? data.write(to: tagsURL)
        }
    }
}
