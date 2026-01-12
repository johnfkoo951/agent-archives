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
    
    private let sessionService = SessionService()
    
    init() {
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
        if searchText.isEmpty {
            filteredSessions = sessions
        } else {
            let query = searchText.lowercased()
            filteredSessions = sessions.filter { session in
                session.title.lowercased().contains(query) ||
                session.project.lowercased().contains(query) ||
                session.preview.lowercased().contains(query)
            }
        }
    }
    
    func switchAgent(_ agent: AgentType) {
        selectedAgent = agent
        selectedSession = nil
        Task { await loadSessions() }
    }
}
