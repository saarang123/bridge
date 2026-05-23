import SwiftUI

struct PodcastAppView: View {
    let app: MiniApp

    private var generateAction: BridgeAction? {
        app.actions.first { action in
            action.name.contains("generate") || action.title.localizedCaseInsensitiveContains("generate")
        }
    }

    private var sourceAction: BridgeAction? {
        app.actions.first { action in
            action.name.contains("source") || action.title.localizedCaseInsensitiveContains("source")
        }
    }

    private var episodeAction: BridgeAction? {
        app.actions.first { action in
            action.name.contains("episode") && !action.name.contains("generate")
        }
    }

    var body: some View {
        List {
            Section {
                VStack(alignment: .leading, spacing: 8) {
                    Label(app.title, systemImage: "headphones")
                        .font(.title2.weight(.semibold))
                    Text(app.description.isEmpty ? "Generate narrated episodes from documents and links." : app.description)
                        .foregroundStyle(.secondary)
                }
                .padding(.vertical, 6)
            }

            Section("Create") {
                if let generateAction {
                    NavigationLink {
                        PodcastGenerateView(
                            app: app,
                            action: generateAction,
                            sourceAction: sourceAction
                        )
                    } label: {
                        Label("Generate Episode", systemImage: "plus.circle")
                    }
                } else {
                    Text("No generate action found.")
                        .foregroundStyle(.secondary)
                }
            }

            Section("Library") {
                if let sourceAction {
                    NavigationLink {
                        ActionRunnerView(app: app, action: sourceAction)
                    } label: {
                        Label("Sources", systemImage: "doc.text")
                    }
                }

                if let episodeAction {
                    NavigationLink {
                        ActionRunnerView(app: app, action: episodeAction)
                    } label: {
                        Label("Episodes", systemImage: "music.note.list")
                    }
                }
            }

            Section("All Actions") {
                ForEach(app.actions) { action in
                    NavigationLink {
                        ActionRunnerView(app: app, action: action)
                    } label: {
                        Text(action.title)
                    }
                }
            }
        }
        .navigationTitle("Podcast")
    }
}

struct PodcastGenerateView: View {
    @EnvironmentObject private var client: BridgeClient
    let app: MiniApp
    let action: BridgeAction
    let sourceAction: BridgeAction?

    @State private var sourceURI = ""
    @State private var result: JSONValue?
    @State private var sources: [PodcastSourceOption] = []
    @State private var sourceSearch = ""
    @State private var sourceLoadError: String?
    @State private var isSubmitting = false
    @State private var isLoadingSources = false

    var body: some View {
        Form {
            Section("Selected Source") {
                TextField("Server path or URL", text: $sourceURI, axis: .vertical)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    .lineLimit(2...5)
            }

            Section {
                Button {
                    Task { await submit() }
                } label: {
                    HStack {
                        Text(isSubmitting ? "Starting..." : "Generate Episode")
                        Spacer()
                        if isSubmitting {
                            ProgressView()
                        }
                    }
                }
                .disabled(sourceURI.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || isSubmitting)
            }

            if sourceAction != nil {
                Section("Server Docs") {
                    TextField("Search sources", text: $sourceSearch)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()

                    if isLoadingSources {
                        ProgressView()
                    } else if let sourceLoadError {
                        Text(sourceLoadError)
                            .foregroundStyle(.secondary)
                    } else if filteredSources.isEmpty {
                        Text("No sources found.")
                            .foregroundStyle(.secondary)
                    } else {
                        Text(sourceCountText)
                            .font(.caption)
                            .foregroundStyle(.secondary)

                        ForEach(visibleSources) { source in
                            Button {
                                sourceURI = source.sourceURI
                            } label: {
                                HStack(alignment: .top, spacing: 10) {
                                    Image(systemName: sourceURI == source.sourceURI ? "checkmark.circle.fill" : "doc.text")
                                        .foregroundStyle(sourceURI == source.sourceURI ? .blue : .secondary)
                                        .frame(width: 22)

                                    VStack(alignment: .leading, spacing: 4) {
                                        Text(source.title)
                                            .foregroundStyle(.primary)
                                        Text(source.sourceURI)
                                            .font(.caption)
                                            .foregroundStyle(.secondary)
                                            .lineLimit(2)
                                    }
                                }
                            }
                        }
                    }
                }
            }

            if let result {
                Section("Result") {
                    JSONValueView(value: result)
                    Text("Track progress in Active.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
        }
        .navigationTitle("Generate")
        .toolbar {
            if !sourceURI.isEmpty {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Clear") {
                        sourceURI = ""
                    }
                }
            }
        }
        .task {
            await loadSources()
        }
    }

    private var filteredSources: [PodcastSourceOption] {
        let query = sourceSearch.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !query.isEmpty else { return sources }
        return sources.filter { source in
            source.title.localizedCaseInsensitiveContains(query)
                || source.sourceURI.localizedCaseInsensitiveContains(query)
                || source.kind.localizedCaseInsensitiveContains(query)
        }
    }

    private var visibleSources: [PodcastSourceOption] {
        Array(filteredSources.prefix(50))
    }

    private var sourceCountText: String {
        if filteredSources.count > visibleSources.count {
            return "Showing \(visibleSources.count) of \(filteredSources.count) matches"
        }
        return "\(filteredSources.count) sources"
    }

    private func loadSources() async {
        guard let sourceAction else { return }
        isLoadingSources = true
        defer { isLoadingSources = false }

        do {
            let value = try await client.invoke(app: app, action: sourceAction, body: [:])
            sources = PodcastSourceOption.options(from: value)
            sourceLoadError = nil
        } catch {
            sourceLoadError = error.localizedDescription
        }
    }

    private func submit() async {
        isSubmitting = true
        defer { isSubmitting = false }

        do {
            let body = bestEffortBody()
            let result = try await client.invoke(app: app, action: action, body: body)
            self.result = result ?? .string("Started")
        } catch {
            result = .string(error.localizedDescription)
        }
    }

    private func bestEffortBody() -> [String: JSONValue] {
        let properties = action.inputSchema.properties ?? [:]
        let key = properties.keys.first { key in
            key == "source_uri" || key == "source" || key == "url" || key == "path"
        } ?? properties.keys.first ?? "source_uri"
        return [key: .string(sourceURI.trimmingCharacters(in: .whitespacesAndNewlines))]
    }
}

struct PodcastSourceOption: Identifiable {
    let id: String
    let title: String
    let sourceURI: String
    let kind: String

    static func options(from value: JSONValue?) -> [PodcastSourceOption] {
        guard case .array(let values) = value else { return [] }

        return values.compactMap { value in
            guard case .object(let object) = value else { return nil }
            let sourceURI = object["source_uri"]?.stringValue
                ?? object["uri"]?.stringValue
                ?? object["path"]?.stringValue
                ?? object["url"]?.stringValue
            guard let sourceURI else { return nil }
            let title = object["title"]?.stringValue ?? sourceURI
            let kind = object["kind"]?.stringValue ?? "source"
            return PodcastSourceOption(id: sourceURI, title: title, sourceURI: sourceURI, kind: kind)
        }
    }
}
