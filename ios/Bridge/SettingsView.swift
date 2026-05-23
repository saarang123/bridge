import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var client: BridgeClient

    var body: some View {
        NavigationStack {
            Form {
                Section("Server") {
                    Toggle("Use Mock Data", isOn: $client.useMockData)

                    TextField("Bridge URL", text: $client.serverURLString)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .keyboardType(.URL)
                        .disabled(client.useMockData)

                    Button {
                        Task { await client.refresh() }
                    } label: {
                        Label("Refresh", systemImage: "arrow.clockwise")
                    }
                }

                Section("Status") {
                    LabeledContent("Apps", value: "\(client.apps.count)")
                    LabeledContent("Activities", value: "\(client.activities.count)")
                    if let error = client.lastError {
                        Text(error)
                            .foregroundStyle(.red)
                    } else {
                        Text("Connected")
                            .foregroundStyle(.secondary)
                    }
                }
            }
            .navigationTitle("Settings")
        }
    }
}
