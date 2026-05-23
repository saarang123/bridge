import SwiftUI

struct AppsView: View {
    @EnvironmentObject private var client: BridgeClient

    var body: some View {
        NavigationStack {
            List {
                podcastSection
                otherAppsSection
            }
            .navigationTitle("Bridge")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        Task { await client.refresh() }
                    } label: {
                        Image(systemName: "arrow.clockwise")
                    }
                }
            }
            .overlay {
                if client.apps.isEmpty && client.isLoading {
                    ProgressView()
                }
            }
        }
    }

    private var podcastSection: some View {
        Section("Podcast") {
            if let podcast = preferredPodcastApp {
                NavigationLink {
                    PodcastAppView(app: podcast)
                } label: {
                    AppRow(app: podcast, systemImage: "headphones")
                }
            } else {
                MissingPodcastView()
            }
        }
    }

    private var otherAppsSection: some View {
        Section("Other Mini-Apps") {
            ForEach(client.apps.filter { $0.name != preferredPodcastApp?.name }) { app in
                NavigationLink {
                    GenericAppView(app: app)
                } label: {
                    AppRow(app: app, systemImage: symbolName(for: app))
                }
            }
        }
    }

    private var preferredPodcastApp: MiniApp? {
        client.apps.first { app in
            app.name == "podcast" || app.name == "podcast-this" || app.title.localizedCaseInsensitiveContains("podcast")
        }
    }

    private func symbolName(for app: MiniApp) -> String {
        switch app.icon {
        case "headphones": return "headphones"
        case "hammer": return "hammer"
        default: return "app"
        }
    }
}

struct AppRow: View {
    let app: MiniApp
    let systemImage: String

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: systemImage)
                .font(.title3)
                .frame(width: 32, height: 32)
                .foregroundStyle(.white)
                .background(Color.accentColor, in: RoundedRectangle(cornerRadius: 7))

            VStack(alignment: .leading, spacing: 3) {
                Text(app.title)
                    .font(.headline)
                if !app.description.isEmpty {
                    Text(app.description)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                        .lineLimit(2)
                }
            }
        }
        .padding(.vertical, 4)
    }
}

struct MissingPodcastView: View {
    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Label("Podcast mini-app not registered", systemImage: "headphones")
                .font(.headline)
            Text("Bridge is reachable, but Podcast This is not in the app manifest yet.")
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
        .padding(.vertical, 6)
    }
}
