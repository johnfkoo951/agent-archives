import SwiftUI

struct ContentView: View {
    @Environment(AppState.self) private var appState
    
    var body: some View {
        @Bindable var state = appState
        
        NavigationSplitView {
            SidebarView()
                .navigationSplitViewColumnWidth(min: 280, ideal: 320, max: 400)
        } detail: {
            DetailView()
        }
        .navigationSplitViewStyle(.balanced)
        .toolbar {
            ToolbarItemGroup(placement: .primaryAction) {
                AgentPicker()
                TabPicker()
            }
        }
    }
}

struct AgentPicker: View {
    @Environment(AppState.self) private var appState
    
    var body: some View {
        @Bindable var state = appState
        
        Picker("Agent", selection: $state.selectedAgent) {
            ForEach(AgentType.allCases, id: \.self) { agent in
                Text(agent.rawValue).tag(agent)
            }
        }
        .pickerStyle(.segmented)
        .frame(width: 200)
        .onChange(of: appState.selectedAgent) { _, newValue in
            appState.switchAgent(newValue)
        }
    }
}

struct TabPicker: View {
    @Environment(AppState.self) private var appState
    
    var body: some View {
        @Bindable var state = appState
        
        Picker("View", selection: $state.selectedTab) {
            Label("Sessions", systemImage: "bubble.left.and.bubble.right")
                .tag(AppTab.sessions)
            Label("Dashboard", systemImage: "chart.bar")
                .tag(AppTab.dashboard)
            Label("Monitor", systemImage: "gauge.with.dots.needle.bottom.50percent")
                .tag(AppTab.monitor)
        }
        .pickerStyle(.segmented)
        .frame(width: 280)
    }
}

#Preview {
    ContentView()
        .environment(AppState())
}
