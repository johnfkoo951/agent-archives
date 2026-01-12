import SwiftUI

struct SidebarView: View {
    @Environment(AppState.self) private var appState
    
    var body: some View {
        @Bindable var state = appState
        
        VStack(spacing: 0) {
            SearchField(text: $state.searchText)
                .padding()
            
            if appState.isLoading {
                ProgressView()
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else if appState.filteredSessions.isEmpty {
                EmptySessionsView()
            } else {
                SessionListView()
            }
            
            StatsBar()
        }
        .navigationTitle(appState.selectedAgent.rawValue)
    }
}

struct SearchField: View {
    @Binding var text: String
    @FocusState private var isFocused: Bool
    
    var body: some View {
        HStack {
            Image(systemName: "magnifyingglass")
                .foregroundStyle(.secondary)
            
            TextField("Search sessions...", text: $text)
                .textFieldStyle(.plain)
                .focused($isFocused)
            
            if !text.isEmpty {
                Button {
                    text = ""
                } label: {
                    Image(systemName: "xmark.circle.fill")
                        .foregroundStyle(.secondary)
                }
                .buttonStyle(.plain)
            }
        }
        .padding(8)
        .background(.quaternary)
        .clipShape(RoundedRectangle(cornerRadius: 8))
    }
}

struct EmptySessionsView: View {
    @Environment(AppState.self) private var appState
    
    var body: some View {
        ContentUnavailableView {
            Label("No Sessions", systemImage: "bubble.left.and.bubble.right")
        } description: {
            if !appState.searchText.isEmpty {
                Text("No sessions match '\(appState.searchText)'")
            } else {
                Text("No sessions found for \(appState.selectedAgent.rawValue)")
            }
        }
    }
}

struct SessionListView: View {
    @Environment(AppState.self) private var appState
    
    var body: some View {
        @Bindable var state = appState
        
        List(appState.filteredSessions, selection: $state.selectedSession) { session in
            SessionRow(session: session)
                .tag(session)
        }
        .listStyle(.sidebar)
    }
}

struct SessionRow: View {
    let session: Session
    @Environment(AppState.self) private var appState
    
    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack {
                Text(session.displayTitle)
                    .font(.headline)
                    .lineLimit(1)
                
                Spacer()
                
                Text("\(session.messageCount)")
                    .font(.caption)
                    .padding(.horizontal, 6)
                    .padding(.vertical, 2)
                    .background(.quaternary)
                    .clipShape(Capsule())
            }
            
            Text(session.preview)
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .lineLimit(2)
            
            HStack {
                Image(systemName: "folder")
                    .font(.caption2)
                Text(session.projectName)
                    .font(.caption)
                
                Spacer()
                
                Text(session.relativeTime)
                    .font(.caption)
                    .foregroundStyle(.tertiary)
            }
            .foregroundStyle(.secondary)
        }
        .padding(.vertical, 4)
    }
}

struct StatsBar: View {
    @Environment(AppState.self) private var appState
    
    var body: some View {
        HStack {
            Label("\(appState.filteredSessions.count) sessions", systemImage: "bubble.left.and.bubble.right")
            
            Spacer()
            
            let totalMessages = appState.filteredSessions.reduce(0) { $0 + $1.messageCount }
            Label("\(totalMessages) messages", systemImage: "text.bubble")
        }
        .font(.caption)
        .foregroundStyle(.secondary)
        .padding()
        .background(.bar)
    }
}

#Preview {
    SidebarView()
        .environment(AppState())
        .frame(width: 300)
}
