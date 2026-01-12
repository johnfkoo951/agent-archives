import Foundation

struct Session: Identifiable, Codable, Hashable {
    let id: String
    let title: String
    let project: String
    let preview: String
    let messageCount: Int
    let lastActivity: Date
    let firstTimestamp: Date?
    let customName: String?
    let tags: [String]
    let projectFolder: String?
    let fileName: String?
    
    var displayTitle: String {
        customName ?? preview.prefix(50).description
    }
    
    var projectName: String {
        project.components(separatedBy: "/").last ?? project
    }
    
    var relativeTime: String {
        let formatter = RelativeDateTimeFormatter()
        formatter.unitsStyle = .abbreviated
        return formatter.localizedString(for: lastActivity, relativeTo: Date())
    }
    
    enum CodingKeys: String, CodingKey {
        case id = "sessionId"
        case title
        case project
        case preview
        case messageCount
        case lastActivity = "lastTimestamp"
        case firstTimestamp
        case customName
        case tags
        case projectFolder
        case fileName
    }
    
    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        title = try container.decodeIfPresent(String.self, forKey: .title) ?? ""
        project = try container.decodeIfPresent(String.self, forKey: .project) ?? ""
        preview = try container.decodeIfPresent(String.self, forKey: .preview) ?? ""
        messageCount = try container.decodeIfPresent(Int.self, forKey: .messageCount) ?? 0
        customName = try container.decodeIfPresent(String.self, forKey: .customName)
        tags = try container.decodeIfPresent([String].self, forKey: .tags) ?? []
        projectFolder = try container.decodeIfPresent(String.self, forKey: .projectFolder)
        fileName = try container.decodeIfPresent(String.self, forKey: .fileName)
        
        if let timestamp = try container.decodeIfPresent(String.self, forKey: .lastActivity) {
            lastActivity = ISO8601DateFormatter().date(from: timestamp) ?? Date()
        } else {
            lastActivity = Date()
        }
        
        if let timestamp = try container.decodeIfPresent(String.self, forKey: .firstTimestamp) {
            firstTimestamp = ISO8601DateFormatter().date(from: timestamp)
        } else {
            firstTimestamp = nil
        }
    }
    
    init(id: String, title: String, project: String, preview: String, messageCount: Int, lastActivity: Date, firstTimestamp: Date? = nil, customName: String? = nil, tags: [String] = [], projectFolder: String? = nil, fileName: String? = nil) {
        self.id = id
        self.title = title
        self.project = project
        self.preview = preview
        self.messageCount = messageCount
        self.lastActivity = lastActivity
        self.firstTimestamp = firstTimestamp
        self.customName = customName
        self.tags = tags
        self.projectFolder = projectFolder
        self.fileName = fileName
    }
}
