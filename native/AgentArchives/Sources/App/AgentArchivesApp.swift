import SwiftUI

@main
struct AgentArchivesApp: App {
    @State private var appState = AppState()
    
    var body: some Scene {
        WindowGroup {
            ContentView()
                .environment(appState)
                .onOpenURL { url in
                    handleDeepLink(url)
                }
        }
        .windowStyle(.automatic)
        .defaultSize(width: 1200, height: 800)
        .handlesExternalEvents(matching: ["agentarchives"])
        .commands {
            CommandGroup(replacing: .newItem) { }
            
            CommandMenu("Sessions") {
                Button("Refresh") {
                    Task { await appState.loadSessions() }
                }
                .keyboardShortcut("r", modifiers: .command)
                
                Divider()
                
                Button("Search...") {
                    appState.isSearchFocused = true
                }
                .keyboardShortcut("f", modifiers: .command)
            }
            
            CommandMenu("View") {
                Button("Sessions") {
                    appState.selectedTab = .sessions
                }
                .keyboardShortcut("1", modifiers: .command)
                
                Button("Dashboard") {
                    appState.selectedTab = .dashboard
                }
                .keyboardShortcut("2", modifiers: .command)
                
                Button("Monitor") {
                    appState.selectedTab = .monitor
                }
                .keyboardShortcut("3", modifiers: .command)
            }
        }
        
        Settings {
            SettingsView()
                .environment(appState)
        }
    }
    
    private func handleDeepLink(_ url: URL) {
        guard url.scheme == "agentarchives" else { return }
        
        if url.host == "session", let sessionId = url.pathComponents.dropFirst().first {
            if let session = appState.sessions.first(where: { $0.id == sessionId }) {
                appState.selectedSession = session
                appState.selectedTab = .sessions
            }
        }
    }
}
