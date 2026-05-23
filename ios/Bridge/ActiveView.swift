import SwiftUI

struct ActiveView: View {
    @EnvironmentObject private var client: BridgeClient
    @State private var filter = ActivityFilter.all

    var body: some View {
        NavigationStack {
            List {
                Picker("Filter", selection: $filter) {
                    ForEach(ActivityFilter.allCases, id: \.self) { filter in
                        Text(filter.title).tag(filter)
                    }
                }
                .pickerStyle(.segmented)

                ForEach(filteredActivities) { activity in
                    NavigationLink {
                        ActivityDetailView(activity: activity)
                    } label: {
                        ActivityRow(activity: activity)
                    }
                }
            }
            .navigationTitle("Active")
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
                if filteredActivities.isEmpty {
                    ContentUnavailableView("Nothing Active", systemImage: "tray")
                }
            }
        }
        .task {
            while !Task.isCancelled {
                await client.refresh()
                try? await Task.sleep(for: .seconds(5))
            }
        }
    }

    private var filteredActivities: [Activity] {
        client.activeItems.filter { activity in
            switch filter {
            case .all:
                return true
            case .jobs:
                return activity.kind == "job"
            case .sessions:
                return activity.kind == "session"
            }
        }
    }
}

enum ActivityFilter: CaseIterable {
    case all
    case jobs
    case sessions

    var title: String {
        switch self {
        case .all: return "All"
        case .jobs: return "Jobs"
        case .sessions: return "Sessions"
        }
    }
}

struct ActivityRow: View {
    let activity: Activity

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(activity.title)
                    .font(.headline)
                Spacer()
                StatusBadge(status: activity.status)
            }

            HStack(spacing: 8) {
                Text(activity.app)
                Text(activity.kind)
                if !activity.phase.isEmpty {
                    Text(activity.phase)
                }
            }
            .font(.caption)
            .foregroundStyle(.secondary)

            if !activity.summary.isEmpty {
                Text(activity.summary)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .lineLimit(2)
            }
        }
        .padding(.vertical, 4)
    }
}

struct ActivityDetailView: View {
    @EnvironmentObject private var client: BridgeClient
    let activity: Activity

    var body: some View {
        List {
            Section {
                ActivityRow(activity: activity)
            }

            Section("Details") {
                LabeledContent("App", value: activity.app)
                LabeledContent("Kind", value: activity.kind)
                LabeledContent("Status", value: activity.status)
                LabeledContent("Phase", value: activity.phase)
                LabeledContent("Updated", value: activity.updatedAt)
            }

            if activity.actions.contains("cancel") {
                Section {
                    Button(role: .destructive) {
                        Task { await client.cancel(activity: activity) }
                    } label: {
                        Label("Cancel", systemImage: "xmark.circle")
                    }
                }
            }

            if let detailURL = activity.detailURL, let url = URL(string: detailURL) {
                Section {
                    Link(destination: url) {
                        Label("Open Result", systemImage: "play.circle")
                    }
                }
            }
        }
        .navigationTitle("Activity")
    }
}

struct StatusBadge: View {
    let status: String

    var body: some View {
        Text(status.capitalized)
            .font(.caption.weight(.semibold))
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .foregroundStyle(color)
            .background(color.opacity(0.12), in: Capsule())
    }

    private var color: Color {
        switch status {
        case "running": return .blue
        case "waiting": return .orange
        case "complete": return .green
        case "failed", "cancelled": return .red
        default: return .secondary
        }
    }
}
