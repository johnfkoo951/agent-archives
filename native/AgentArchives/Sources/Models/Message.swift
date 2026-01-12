import Foundation

enum MessageRole: String, Codable {
    case user
    case assistant
}

struct Message: Identifiable, Codable {
    let id: UUID
    let role: MessageRole
    let content: String
    let timestamp: Date?
    let toolUses: [ToolUse]?
    
    init(id: UUID = UUID(), role: MessageRole, content: String, timestamp: Date? = nil, toolUses: [ToolUse]? = nil) {
        self.id = id
        self.role = role
        self.content = content
        self.timestamp = timestamp
        self.toolUses = toolUses
    }
}

struct ToolUse: Identifiable, Codable {
    let id: String
    let name: String
    let input: String
    
    var displayName: String {
        name.replacingOccurrences(of: "_", with: " ").capitalized
    }
}

struct ConversationData: Codable {
    let messages: [RawMessage]
    
    struct RawMessage: Codable {
        let type: String
        let message: MessageContent?
        let timestamp: String?
        
        struct MessageContent: Codable {
            let role: String?
            let content: ContentValue?
        }
    }
}

enum ContentValue: Codable {
    case string(String)
    case array([ContentItem])
    
    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if let string = try? container.decode(String.self) {
            self = .string(string)
        } else if let array = try? container.decode([ContentItem].self) {
            self = .array(array)
        } else {
            self = .string("")
        }
    }
    
    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        switch self {
        case .string(let s): try container.encode(s)
        case .array(let a): try container.encode(a)
        }
    }
    
    var textContent: String {
        switch self {
        case .string(let s): return s
        case .array(let items):
            return items.compactMap { item -> String? in
                if item.type == "text" { return item.text }
                return nil
            }.joined(separator: "\n")
        }
    }
}

struct ContentItem: Codable {
    let type: String
    let text: String?
    let name: String?
    let input: AnyCodable?
    let id: String?
}

struct AnyCodable: Codable {
    let value: Any
    
    init(_ value: Any) {
        self.value = value
    }
    
    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if let dict = try? container.decode([String: AnyCodable].self) {
            value = dict.mapValues { $0.value }
        } else if let array = try? container.decode([AnyCodable].self) {
            value = array.map { $0.value }
        } else if let string = try? container.decode(String.self) {
            value = string
        } else if let int = try? container.decode(Int.self) {
            value = int
        } else if let double = try? container.decode(Double.self) {
            value = double
        } else if let bool = try? container.decode(Bool.self) {
            value = bool
        } else {
            value = ""
        }
    }
    
    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        if let string = value as? String {
            try container.encode(string)
        } else if let int = value as? Int {
            try container.encode(int)
        } else if let double = value as? Double {
            try container.encode(double)
        } else if let bool = value as? Bool {
            try container.encode(bool)
        } else {
            try container.encodeNil()
        }
    }
}
