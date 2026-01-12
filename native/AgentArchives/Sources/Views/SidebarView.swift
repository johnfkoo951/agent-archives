import SwiftUI

struct SidebarView: View {
    @Environment(AppState.self) private var appState
    
    var body: some View {
        @Bindable var state = appState
        
        VStack(spacing: 0) {
            SearchField(text: $state.searchText)
                .padding(.horizontal)
                .padding(.top)
            
            if !appState.allTags.isEmpty {
                TagFilterBar()
                    .padding(.horizontal)
                    .padding(.top, 8)
            }
            
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

struct TagFilterBar: View {
    @Environment(AppState.self) private var appState
    
    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 6) {
                TagButton(tag: nil, label: "All", isSelected: appState.selectedTag == nil)
                
                ForEach(appState.allTags, id: \.self) { tag in
                    TagButton(tag: tag, label: tag, isSelected: appState.selectedTag == tag)
                }
            }
        }
    }
}

struct TagButton: View {
    @Environment(AppState.self) private var appState
    let tag: String?
    let label: String
    let isSelected: Bool
    
    var body: some View {
        Button {
            appState.selectedTag = tag
            appState.filterSessions()
        } label: {
            Text(label)
                .font(.caption)
                .padding(.horizontal, 10)
                .padding(.vertical, 4)
                .background(isSelected ? Color.accentColor : Color.secondary.opacity(0.2))
                .foregroundStyle(isSelected ? .white : .primary)
                .clipShape(Capsule())
        }
        .buttonStyle(.plain)
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
    @State private var showRenameSheet = false
    @State private var showTagSheet = false
    @State private var newName = ""
    @State private var newTag = ""
    
    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack {
                Text(appState.getDisplayName(for: session))
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
                
                let tags = appState.getTags(for: session.id)
                if !tags.isEmpty {
                    HStack(spacing: 2) {
                        ForEach(tags.prefix(2), id: \.self) { tag in
                            Text(tag)
                                .font(.system(size: 9))
                                .padding(.horizontal, 4)
                                .padding(.vertical, 1)
                                .background(.blue.opacity(0.2))
                                .clipShape(Capsule())
                        }
                        if tags.count > 2 {
                            Text("+\(tags.count - 2)")
                                .font(.system(size: 9))
                                .foregroundStyle(.secondary)
                        }
                    }
                }
                
                Text(session.relativeTime)
                    .font(.caption)
                    .foregroundStyle(.tertiary)
            }
            .foregroundStyle(.secondary)
        }
        .padding(.vertical, 4)
        .contextMenu {
            Button {
                newName = appState.sessionNames[session.id] ?? ""
                showRenameSheet = true
            } label: {
                Label("Rename", systemImage: "pencil")
            }
            
            Button {
                showTagSheet = true
            } label: {
                Label("Manage Tags", systemImage: "tag")
            }
            
            Divider()
            
            if appState.selectedAgent == .claude {
                Button {
                    resumeSession(session)
                } label: {
                    Label("Resume in Terminal", systemImage: "terminal")
                }
            }
            
            Button {
                NSPasteboard.general.clearContents()
                NSPasteboard.general.setString(session.id, forType: .string)
            } label: {
                Label("Copy Session ID", systemImage: "doc.on.doc")
            }
        }
        .sheet(isPresented: $showRenameSheet) {
            RenameSheet(sessionId: session.id, currentName: $newName)
        }
        .sheet(isPresented: $showTagSheet) {
            TagSheet(sessionId: session.id)
        }
    }
}

private func resumeSession(_ session: Session) {
    let script = """
    tell application "Terminal"
        activate
        do script "claude --resume \(session.id)"
    end tell
    """
    
    var error: NSDictionary?
    if let scriptObject = NSAppleScript(source: script) {
        scriptObject.executeAndReturnError(&error)
    }
}

struct RenameSheet: View {
    @Environment(AppState.self) private var appState
    @Environment(\.dismiss) private var dismiss
    let sessionId: String
    @Binding var currentName: String
    
    var body: some View {
        VStack(spacing: 16) {
            Text("Rename Session")
                .font(.headline)
            
            TextField("Session name", text: $currentName)
                .textFieldStyle(.roundedBorder)
                .frame(width: 300)
            
            HStack {
                Button("Cancel") { dismiss() }
                    .keyboardShortcut(.escape)
                
                Button("Save") {
                    appState.setSessionName(currentName, for: sessionId)
                    dismiss()
                }
                .keyboardShortcut(.return)
                .buttonStyle(.borderedProminent)
            }
        }
        .padding()
    }
}

struct TagSheet: View {
    @Environment(AppState.self) private var appState
    @Environment(\.dismiss) private var dismiss
    let sessionId: String
    @State private var newTag = ""
    
    var body: some View {
        VStack(spacing: 16) {
            Text("Manage Tags")
                .font(.headline)
            
            let tags = appState.getTags(for: sessionId)
            if !tags.isEmpty {
                FlowLayout(spacing: 6) {
                    ForEach(tags, id: \.self) { tag in
                        HStack(spacing: 4) {
                            Text(tag)
                            Button {
                                appState.removeTag(tag, from: sessionId)
                            } label: {
                                Image(systemName: "xmark.circle.fill")
                                    .font(.caption)
                            }
                            .buttonStyle(.plain)
                        }
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(.blue.opacity(0.2))
                        .clipShape(Capsule())
                    }
                }
                .frame(width: 300)
            }
            
            HStack {
                TextField("New tag", text: $newTag)
                    .textFieldStyle(.roundedBorder)
                
                Button {
                    if !newTag.isEmpty {
                        appState.addTag(newTag, to: sessionId)
                        newTag = ""
                    }
                } label: {
                    Image(systemName: "plus.circle.fill")
                }
                .disabled(newTag.isEmpty)
            }
            .frame(width: 300)
            
            if !appState.allTags.isEmpty {
                Text("Existing tags:")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                
                FlowLayout(spacing: 6) {
                    ForEach(appState.allTags.filter { !tags.contains($0) }, id: \.self) { tag in
                        Button {
                            appState.addTag(tag, to: sessionId)
                        } label: {
                            Text(tag)
                                .font(.caption)
                                .padding(.horizontal, 8)
                                .padding(.vertical, 4)
                                .background(.secondary.opacity(0.2))
                                .clipShape(Capsule())
                        }
                        .buttonStyle(.plain)
                    }
                }
                .frame(width: 300)
            }
            
            Button("Done") { dismiss() }
                .keyboardShortcut(.return)
        }
        .padding()
    }
}

struct FlowLayout: Layout {
    var spacing: CGFloat = 8
    
    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let result = arrange(proposal: proposal, subviews: subviews)
        return result.size
    }
    
    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        let result = arrange(proposal: proposal, subviews: subviews)
        for (index, position) in result.positions.enumerated() {
            subviews[index].place(at: CGPoint(x: bounds.minX + position.x, y: bounds.minY + position.y), proposal: .unspecified)
        }
    }
    
    private func arrange(proposal: ProposedViewSize, subviews: Subviews) -> (positions: [CGPoint], size: CGSize) {
        let maxWidth = proposal.width ?? .infinity
        var positions: [CGPoint] = []
        var x: CGFloat = 0
        var y: CGFloat = 0
        var rowHeight: CGFloat = 0
        
        for subview in subviews {
            let size = subview.sizeThatFits(.unspecified)
            if x + size.width > maxWidth && x > 0 {
                x = 0
                y += rowHeight + spacing
                rowHeight = 0
            }
            positions.append(CGPoint(x: x, y: y))
            rowHeight = max(rowHeight, size.height)
            x += size.width + spacing
        }
        
        return (positions, CGSize(width: maxWidth, height: y + rowHeight))
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
