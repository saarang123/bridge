import SwiftUI

struct GenericAppView: View {
    let app: MiniApp

    var body: some View {
        List {
            Section {
                VStack(alignment: .leading, spacing: 6) {
                    Text(app.title)
                        .font(.title2.weight(.semibold))
                    Text(app.description)
                        .foregroundStyle(.secondary)
                }
                .padding(.vertical, 6)
            }

            Section("Actions") {
                ForEach(app.actions) { action in
                    NavigationLink {
                        ActionRunnerView(app: app, action: action)
                    } label: {
                        VStack(alignment: .leading, spacing: 3) {
                            Text(action.title)
                            if !action.description.isEmpty {
                                Text(action.description)
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                        }
                    }
                }
            }
        }
        .navigationTitle(app.title)
    }
}

struct ActionRunnerView: View {
    @EnvironmentObject private var client: BridgeClient
    let app: MiniApp
    let action: BridgeAction

    @State private var values: [String: String] = [:]
    @State private var result: JSONValue?
    @State private var isSubmitting = false

    var body: some View {
        Form {
            if !inputFields.isEmpty {
                Section("Input") {
                    ForEach(inputFields, id: \.self) { field in
                        TextField(fieldTitle(field), text: binding(for: field), axis: .vertical)
                            .textInputAutocapitalization(.never)
                            .autocorrectionDisabled()
                    }
                }
            }

            Section {
                Button {
                    Task { await run() }
                } label: {
                    HStack {
                        Text(buttonTitle)
                        Spacer()
                        if isSubmitting {
                            ProgressView()
                        }
                    }
                }
                .disabled(isSubmitting)
            }

            if let result {
                Section("Result") {
                    JSONValueView(value: result)
                }
            }
        }
        .navigationTitle(action.title)
    }

    private var inputFields: [String] {
        (action.inputSchema.properties ?? [:]).keys.sorted()
    }

    private var buttonTitle: String {
        switch action.uiKind {
        case "trigger": return "Run"
        case "form": return "Submit"
        default: return action.method == "GET" ? "Load" : "Run"
        }
    }

    private func binding(for key: String) -> Binding<String> {
        Binding(
            get: { values[key, default: ""] },
            set: { values[key] = $0 }
        )
    }

    private func fieldTitle(_ field: String) -> String {
        field.replacingOccurrences(of: "_", with: " ").capitalized
    }

    private func run() async {
        isSubmitting = true
        defer { isSubmitting = false }

        do {
            let body = values.mapValues { JSONValue.string($0) }
            result = try await client.invoke(app: app, action: action, body: body)
        } catch {
            result = .string(error.localizedDescription)
        }
    }
}
