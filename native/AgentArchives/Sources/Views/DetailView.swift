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
    
    private var totalMessages: Int {
        appState.sessions.reduce(0) { $0 + $1.messageCount }
    }
    
    private var uniqueProjects: Int {
        Set(appState.sessions.map { $0.project }).count
    }
    
    private var thisWeekSessions: Int {
        let weekAgo = Date().addingTimeInterval(-7*24*60*60)
        return appState.sessions.filter { $0.lastActivity > weekAgo }.count
    }
    
    private var todaySessions: Int {
        let calendar = Calendar.current
        return appState.sessions.filter { calendar.isDateInToday($0.lastActivity) }.count
    }
    
    private var projectStats: [(project: String, sessions: Int, messages: Int)] {
        let grouped = Dictionary(grouping: appState.sessions) { $0.projectName }
        return grouped.map { (project: $0.key, sessions: $0.value.count, messages: $0.value.reduce(0) { $0 + $1.messageCount }) }
            .sorted { $0.sessions > $1.sessions }
            .prefix(10)
            .map { $0 }
    }
    
    private var recentActivity: [(date: String, count: Int)] {
        let formatter = DateFormatter()
        formatter.dateFormat = "MM/dd"
        let calendar = Calendar.current
        
        var activity: [String: Int] = [:]
        for i in 0..<14 {
            let date = calendar.date(byAdding: .day, value: -i, to: Date())!
            activity[formatter.string(from: date)] = 0
        }
        
        for session in appState.sessions {
            let key = formatter.string(from: session.lastActivity)
            if activity[key] != nil {
                activity[key]! += 1
            }
        }
        
        return activity.sorted { 
            formatter.date(from: $0.key)! > formatter.date(from: $1.key)!
        }.reversed().map { ($0.key, $0.value) }
    }
    
    var body: some View {
        ScrollView {
            VStack(spacing: 24) {
                LazyVGrid(columns: [
                    GridItem(.flexible()),
                    GridItem(.flexible()),
                    GridItem(.flexible()),
                    GridItem(.flexible())
                ], spacing: 16) {
                    StatCard(title: "Total Sessions", value: "\(appState.sessions.count)", icon: "bubble.left.and.bubble.right", color: .blue)
                    StatCard(title: "Total Messages", value: formatNumber(totalMessages), icon: "text.bubble", color: .purple)
                    StatCard(title: "Projects", value: "\(uniqueProjects)", icon: "folder", color: .orange)
                    StatCard(title: "Today", value: "\(todaySessions)", icon: "sun.max", color: .yellow)
                }
                
                HStack(alignment: .top, spacing: 24) {
                    VStack(alignment: .leading, spacing: 12) {
                        Text("Activity (14 days)")
                            .font(.headline)
                        
                        HStack(alignment: .bottom, spacing: 4) {
                            ForEach(recentActivity, id: \.date) { item in
                                VStack(spacing: 4) {
                                    RoundedRectangle(cornerRadius: 4)
                                        .fill(.blue.opacity(0.8))
                                        .frame(width: 24, height: max(4, CGFloat(item.count) * 8))
                                    Text(item.date)
                                        .font(.system(size: 8))
                                        .foregroundStyle(.secondary)
                                }
                            }
                        }
                        .frame(height: 120, alignment: .bottom)
                        .padding()
                        .background(.regularMaterial)
                        .clipShape(RoundedRectangle(cornerRadius: 12))
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    
                    VStack(alignment: .leading, spacing: 12) {
                        Text("Top Projects")
                            .font(.headline)
                        
                        VStack(spacing: 8) {
                            ForEach(projectStats.prefix(8), id: \.project) { stat in
                                HStack {
                                    Text(stat.project)
                                        .font(.subheadline)
                                        .lineLimit(1)
                                    Spacer()
                                    Text("\(stat.sessions) sessions")
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                }
                            }
                        }
                        .padding()
                        .background(.regularMaterial)
                        .clipShape(RoundedRectangle(cornerRadius: 12))
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                }
            }
            .padding()
        }
        .navigationTitle("Dashboard")
    }
    
    private func formatNumber(_ n: Int) -> String {
        if n >= 1000 {
            return String(format: "%.1fK", Double(n) / 1000.0)
        }
        return "\(n)"
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
    @State private var usageData: UsageData?
    @State private var isLoading = true
    @State private var errorMessage: String?
    
    var body: some View {
        if appState.selectedAgent == .opencode {
            ContentUnavailableView {
                Label("Not Available", systemImage: "gauge.with.dots.needle.bottom.50percent")
            } description: {
                Text("Usage monitoring is only available for Claude Code")
            }
        } else {
            ScrollView {
                VStack(spacing: 24) {
                    if isLoading {
                        ProgressView("Loading usage data...")
                            .frame(maxWidth: .infinity, maxHeight: 200)
                    } else if let error = errorMessage {
                        VStack(spacing: 16) {
                            Image(systemName: "exclamationmark.triangle")
                                .font(.largeTitle)
                                .foregroundStyle(.orange)
                            Text("Could not load usage data")
                                .font(.headline)
                            Text(error)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                            Text("Install claude-monitor: pip3 install claude-monitor")
                                .font(.caption)
                                .padding(8)
                                .background(.quaternary)
                                .clipShape(RoundedRectangle(cornerRadius: 8))
                        }
                        .frame(maxWidth: .infinity)
                        .padding()
                    } else if let data = usageData {
                        LazyVGrid(columns: [
                            GridItem(.flexible()),
                            GridItem(.flexible()),
                            GridItem(.flexible())
                        ], spacing: 16) {
                            StatCard(title: "Total Cost", value: String(format: "$%.2f", data.totalCost), icon: "dollarsign.circle", color: .green)
                            StatCard(title: "Input Tokens", value: formatTokens(data.inputTokens), icon: "arrow.down.circle", color: .blue)
                            StatCard(title: "Output Tokens", value: formatTokens(data.outputTokens), icon: "arrow.up.circle", color: .purple)
                        }
                        
                        VStack(alignment: .leading, spacing: 12) {
                            Text("Daily Usage (14 days)")
                                .font(.headline)
                            
                            if data.dailyUsage.isEmpty {
                                Text("No usage data available")
                                    .foregroundStyle(.secondary)
                                    .frame(maxWidth: .infinity, alignment: .center)
                                    .padding()
                            } else {
                                HStack(alignment: .bottom, spacing: 8) {
                                    ForEach(data.dailyUsage, id: \.date) { day in
                                        VStack(spacing: 4) {
                                            RoundedRectangle(cornerRadius: 4)
                                                .fill(.green.opacity(0.8))
                                                .frame(width: 32, height: max(4, CGFloat(day.cost / data.maxDailyCost) * 100))
                                            Text(day.dateShort)
                                                .font(.system(size: 9))
                                                .foregroundStyle(.secondary)
                                        }
                                    }
                                }
                                .frame(height: 140, alignment: .bottom)
                                .padding()
                                .background(.regularMaterial)
                                .clipShape(RoundedRectangle(cornerRadius: 12))
                            }
                        }
                    }
                }
                .padding()
            }
            .navigationTitle("Monitor")
            .task {
                await loadUsageData()
            }
        }
    }
    
    private func loadUsageData() async {
        isLoading = true
        errorMessage = nil
        
        let task = Process()
        task.executableURL = URL(fileURLWithPath: "/usr/bin/env")
        task.arguments = ["python3", "-c", """
        import json
        try:
            from ccusage import get_usage
            usage = get_usage(days=14)
            print(json.dumps(usage))
        except ImportError:
            print('{"error": "ccusage not installed"}')
        except Exception as e:
            print(json.dumps({"error": str(e)}))
        """]
        
        let pipe = Pipe()
        task.standardOutput = pipe
        task.standardError = pipe
        
        do {
            try task.run()
            task.waitUntilExit()
            
            let data = pipe.fileHandleForReading.readDataToEndOfFile()
            if let output = String(data: data, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines),
               let jsonData = output.data(using: .utf8),
               let json = try? JSONSerialization.jsonObject(with: jsonData) as? [String: Any] {
                
                if let error = json["error"] as? String {
                    errorMessage = error
                } else {
                    usageData = UsageData(from: json)
                }
            } else {
                errorMessage = "Failed to parse usage data"
            }
        } catch {
            errorMessage = error.localizedDescription
        }
        
        isLoading = false
    }
    
    private func formatTokens(_ n: Int) -> String {
        if n >= 1_000_000 {
            return String(format: "%.1fM", Double(n) / 1_000_000.0)
        } else if n >= 1000 {
            return String(format: "%.1fK", Double(n) / 1000.0)
        }
        return "\(n)"
    }
}

struct UsageData {
    let totalCost: Double
    let inputTokens: Int
    let outputTokens: Int
    let dailyUsage: [DailyUsage]
    var maxDailyCost: Double { dailyUsage.map { $0.cost }.max() ?? 1.0 }
    
    struct DailyUsage {
        let date: String
        let cost: Double
        var dateShort: String {
            let parts = date.split(separator: "-")
            if parts.count >= 2 {
                return "\(parts[1])/\(parts.last ?? "")"
            }
            return date
        }
    }
    
    init(from json: [String: Any]) {
        totalCost = json["total_cost"] as? Double ?? 0
        inputTokens = json["input_tokens"] as? Int ?? 0
        outputTokens = json["output_tokens"] as? Int ?? 0
        
        if let daily = json["daily"] as? [[String: Any]] {
            dailyUsage = daily.compactMap { day in
                guard let date = day["date"] as? String,
                      let cost = day["cost"] as? Double else { return nil }
                return DailyUsage(date: date, cost: cost)
            }
        } else {
            dailyUsage = []
        }
    }
}

#Preview {
    DetailView()
        .environment(AppState())
}
