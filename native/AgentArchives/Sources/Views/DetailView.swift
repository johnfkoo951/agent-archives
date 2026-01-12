import SwiftUI

struct DetailView: View {
    @Environment(AppState.self) private var appState
    
    var body: some View {
        switch appState.selectedTab {
        case .sessions:
            SessionDetailView()
        case .dashboard:
            DashboardView()
        case .monitor:
            MonitorView()
        }
    }
}

struct SessionDetailView: View {
    @Environment(AppState.self) private var appState
    
    var body: some View {
        if let session = appState.selectedSession {
            ConversationView(session: session)
        } else {
            ContentUnavailableView {
                Label("Select a Session", systemImage: "bubble.left.and.bubble.right")
            } description: {
                Text("Choose a session from the sidebar to view the conversation")
            }
        }
    }
}

struct ConversationView: View {
    let session: Session
    @Environment(AppState.self) private var appState
    @State private var messages: [Message] = []
    @State private var isLoading = true
    
    var body: some View {
        VStack(spacing: 0) {
            ConversationHeader(session: session)
            
            if isLoading {
                ProgressView("Loading messages...")
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                ScrollView {
                    LazyVStack(spacing: 16) {
                        ForEach(messages) { message in
                            MessageBubble(message: message)
                        }
                    }
                    .padding()
                }
            }
        }
        .task {
            await loadMessages()
        }
        .onChange(of: session) { _, _ in
            Task { await loadMessages() }
        }
    }
    
    private func loadMessages() async {
        isLoading = true
        let service = SessionService()
        do {
            messages = try await service.loadMessages(for: session, agent: appState.selectedAgent)
        } catch {
            messages = []
        }
        isLoading = false
    }
}

struct ConversationHeader: View {
    let session: Session
    
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(session.displayTitle)
                .font(.title2)
                .fontWeight(.semibold)
            
            HStack {
                Label(session.projectName, systemImage: "folder")
                Divider().frame(height: 12)
                Label("\(session.messageCount) messages", systemImage: "bubble.left.and.bubble.right")
                Divider().frame(height: 12)
                Label(session.relativeTime, systemImage: "clock")
            }
            .font(.caption)
            .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
        .background(.bar)
    }
}

struct MessageBubble: View {
    let message: Message
    
    var isUser: Bool { message.role == .user }
    
    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            if !isUser { Spacer(minLength: 60) }
            
            VStack(alignment: isUser ? .trailing : .leading, spacing: 4) {
                HStack {
                    Image(systemName: isUser ? "person.fill" : "sparkles")
                        .foregroundStyle(isUser ? .blue : .purple)
                    
                    Text(isUser ? "You" : "Claude")
                        .font(.caption)
                        .fontWeight(.semibold)
                    
                    if let timestamp = message.timestamp {
                        Text(timestamp, style: .time)
                            .font(.caption2)
                            .foregroundStyle(.tertiary)
                    }
                }
                
                Text(message.content)
                    .font(.body)
                    .textSelection(.enabled)
                    .padding(12)
                    .background(isUser ? Color.blue.opacity(0.1) : Color.secondary.opacity(0.1))
                    .clipShape(RoundedRectangle(cornerRadius: 12))
            }
            
            if isUser { Spacer(minLength: 60) }
        }
    }
}

struct DashboardView: View {
    @Environment(AppState.self) private var appState
    
    var body: some View {
        ScrollView {
            LazyVGrid(columns: [
                GridItem(.flexible()),
                GridItem(.flexible())
            ], spacing: 20) {
                StatCard(
                    title: "Total Sessions",
                    value: "\(appState.sessions.count)",
                    icon: "bubble.left.and.bubble.right",
                    color: .blue
                )
                
                StatCard(
                    title: "Total Messages",
                    value: "\(appState.sessions.reduce(0) { $0 + $1.messageCount })",
                    icon: "text.bubble",
                    color: .purple
                )
                
                StatCard(
                    title: "Projects",
                    value: "\(Set(appState.sessions.map { $0.project }).count)",
                    icon: "folder",
                    color: .orange
                )
                
                StatCard(
                    title: "This Week",
                    value: "\(appState.sessions.filter { $0.lastActivity > Date().addingTimeInterval(-7*24*60*60) }.count)",
                    icon: "calendar",
                    color: .green
                )
            }
            .padding()
        }
        .navigationTitle("Dashboard")
    }
}

struct StatCard: View {
    let title: String
    let value: String
    let icon: String
    let color: Color
    
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Image(systemName: icon)
                    .font(.title2)
                    .foregroundStyle(color)
                Spacer()
            }
            
            Text(value)
                .font(.system(size: 36, weight: .bold, design: .rounded))
            
            Text(title)
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(.regularMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 16))
    }
}

struct MonitorView: View {
    @Environment(AppState.self) private var appState
    
    var body: some View {
        if appState.selectedAgent == .opencode {
            ContentUnavailableView {
                Label("Not Available", systemImage: "gauge.with.dots.needle.bottom.50percent")
            } description: {
                Text("Usage monitoring is only available for Claude Code")
            }
        } else {
            VStack {
                Text("Token Usage Monitor")
                    .font(.title)
                Text("Coming soon...")
                    .foregroundStyle(.secondary)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
    }
}

#Preview {
    DetailView()
        .environment(AppState())
}
