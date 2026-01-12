import SwiftUI

struct SettingsView: View {
    @Environment(AppState.self) private var appState
    @AppStorage("showToolCalls") private var showToolCalls = true
    @AppStorage("renderMarkdown") private var renderMarkdown = true
    @AppStorage("autoRefreshInterval") private var autoRefreshInterval = 60
    
    var body: some View {
        Form {
            Section("Display") {
                Toggle("Show Tool Calls", isOn: $showToolCalls)
                Toggle("Render Markdown", isOn: $renderMarkdown)
            }
            
            Section("Refresh") {
                Picker("Auto Refresh", selection: $autoRefreshInterval) {
                    Text("Off").tag(0)
                    Text("30 seconds").tag(30)
                    Text("1 minute").tag(60)
                    Text("5 minutes").tag(300)
                }
            }
            
            Section("About") {
                LabeledContent("Version", value: Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "1.0.0")
                LabeledContent("Build", value: Bundle.main.infoDictionary?["CFBundleVersion"] as? String ?? "1")
                
                Link(destination: URL(string: "https://github.com/johnfkoo951/agent-archives")!) {
                    Label("GitHub Repository", systemImage: "link")
                }
            }
        }
        .formStyle(.grouped)
        .frame(width: 400)
        .padding()
    }
}

#Preview {
    SettingsView()
        .environment(AppState())
}
