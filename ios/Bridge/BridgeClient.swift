import Foundation

@MainActor
final class BridgeClient: ObservableObject {
    @Published var useMockData: Bool {
        didSet {
            UserDefaults.standard.set(useMockData, forKey: "useMockData")
        }
    }
    @Published var serverURLString: String {
        didSet {
            UserDefaults.standard.set(serverURLString, forKey: "serverURLString")
        }
    }
    @Published private(set) var apps: [MiniApp] = []
    @Published private(set) var activities: [Activity] = []
    @Published private(set) var trackedPodcastJobs: [TrackedPodcastJob] = []
    @Published var isLoading = false
    @Published var lastError: String?

    private let session: URLSession

    init(session: URLSession = .shared) {
        self.session = session
        self.serverURLString = UserDefaults.standard.string(forKey: "serverURLString") ?? "http://127.0.0.1:8080"
        self.useMockData = UserDefaults.standard.bool(forKey: "useMockData")
        self.trackedPodcastJobs = Self.loadTrackedPodcastJobs()
    }

    func refresh() async {
        isLoading = true
        defer { isLoading = false }

        if useMockData {
            apps = MockBridgeData.apps
            activities = MockBridgeData.activities
            lastError = nil
            return
        }

        do {
            async let appsResponse: AppsResponse = get("/apps")
            async let activitiesResponse: ActivitiesResponse = get("/activities")
            apps = try await appsResponse.apps
            activities = try await activitiesResponse.activities
            await pollTrackedPodcastJobs()
            lastError = nil
        } catch {
            lastError = error.localizedDescription
        }
    }

    func invoke(app: MiniApp, action: BridgeAction, body: [String: JSONValue]) async throws -> JSONValue? {
        if useMockData {
            let result = MockBridgeData.invoke(app: app, action: action, body: body)
            await refresh()
            return result
        }

        let path = "/apps/\(app.name)/actions/\(action.name)"
        let envelope: ActionEnvelope
        if action.method == "GET" {
            envelope = try await get(path, query: body)
        } else {
            envelope = try await post(path, body: body)
        }
        if let error = envelope.error {
            throw error
        }
        recordPodcastJobIfNeeded(app: app, action: action, body: body, result: envelope.data)
        await refresh()
        return envelope.data
    }

    var activeItems: [Activity] {
        let tracked = trackedPodcastJobs.map(\.activity)
        let backendIDs = Set(activities.map(\.id))
        return activities + tracked.filter { !backendIDs.contains($0.id) }
    }

    func cancel(activity: Activity) async {
        if useMockData {
            activities.removeAll { $0.id == activity.id }
            return
        }

        do {
            let _: JSONValue = try await post("/activities/\(activity.id)/cancel", body: [:])
            await refresh()
        } catch {
            lastError = error.localizedDescription
        }
    }

    private func get<T: Decodable>(_ path: String, query: [String: JSONValue] = [:]) async throws -> T {
        let requestURL = try url(path, query: query)
        let (data, response) = try await session.data(from: requestURL)
        try validate(response: response, data: data)
        return try JSONDecoder().decode(T.self, from: data)
    }

    private func post<T: Decodable>(_ path: String, body: [String: JSONValue]) async throws -> T {
        var request = URLRequest(url: try url(path))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(body)

        let (data, response) = try await session.data(for: request)
        try validate(response: response, data: data)
        return try JSONDecoder().decode(T.self, from: data)
    }

    private func url(_ path: String, query: [String: JSONValue] = [:]) throws -> URL {
        guard let baseURL = URL(string: serverURLString) else {
            throw URLError(.badURL)
        }
        let url = baseURL.appending(path: path)
        guard !query.isEmpty else { return url }

        var components = URLComponents(url: url, resolvingAgainstBaseURL: false)
        components?.queryItems = query.map { key, value in
            URLQueryItem(name: key, value: value.queryStringValue)
        }
        guard let queryURL = components?.url else {
            throw URLError(.badURL)
        }
        return queryURL
    }

    private func validate(response: URLResponse, data: Data) throws {
        guard let httpResponse = response as? HTTPURLResponse else {
            return
        }
        guard (200..<300).contains(httpResponse.statusCode) else {
            if let envelope = try? JSONDecoder().decode(ActionEnvelope.self, from: data),
               let error = envelope.error {
                throw error
            }
            throw URLError(.badServerResponse)
        }
    }

    private func recordPodcastJobIfNeeded(
        app: MiniApp,
        action: BridgeAction,
        body: [String: JSONValue],
        result: JSONValue?
    ) {
        guard app.name == "podcast", action.name == "generate_episode" else {
            return
        }
        guard case .object(let object) = result,
              let jobID = object["job_id"]?.stringValue else {
            return
        }

        let sourceURI = body["source_uri"]?.stringValue
            ?? body["source"]?.stringValue
            ?? body["url"]?.stringValue
            ?? body["path"]?.stringValue
            ?? ""
        let now = ISO8601DateFormatter().string(from: Date())
        let job = TrackedPodcastJob(
            jobID: jobID,
            sourceURI: sourceURI,
            status: object["status"]?.stringValue ?? "queued",
            phase: "queued",
            message: "",
            audioURL: nil,
            feedURL: nil,
            createdAt: now,
            updatedAt: now
        )

        trackedPodcastJobs.removeAll { $0.jobID == job.jobID }
        trackedPodcastJobs.insert(job, at: 0)
        saveTrackedPodcastJobs()
    }

    func pollTrackedPodcastJobs() async {
        guard !useMockData else { return }
        guard !trackedPodcastJobs.isEmpty else { return }

        var updatedJobs = trackedPodcastJobs
        for index in updatedJobs.indices {
            guard !updatedJobs[index].isTerminal else { continue }
            do {
                let envelope: ActionEnvelope = try await get(
                    "/apps/podcast/actions/get_job",
                    query: ["job_id": .string(updatedJobs[index].jobID)]
                )
                if case .object(let object) = envelope.data {
                    updatedJobs[index].status = object["status"]?.stringValue ?? updatedJobs[index].status
                    updatedJobs[index].phase = object["phase"]?.stringValue ?? updatedJobs[index].phase
                    updatedJobs[index].message = object["message"]?.stringValue ?? updatedJobs[index].message
                    updatedJobs[index].audioURL = object["audio_url"]?.stringValue ?? updatedJobs[index].audioURL
                    updatedJobs[index].feedURL = object["feed_url"]?.stringValue ?? updatedJobs[index].feedURL
                    updatedJobs[index].updatedAt = ISO8601DateFormatter().string(from: Date())
                }
            } catch {
                lastError = error.localizedDescription
            }
        }

        trackedPodcastJobs = updatedJobs
        saveTrackedPodcastJobs()
    }

    private static func loadTrackedPodcastJobs() -> [TrackedPodcastJob] {
        guard let data = UserDefaults.standard.data(forKey: "trackedPodcastJobs") else {
            return []
        }
        return (try? JSONDecoder().decode([TrackedPodcastJob].self, from: data)) ?? []
    }

    private func saveTrackedPodcastJobs() {
        guard let data = try? JSONEncoder().encode(trackedPodcastJobs) else {
            return
        }
        UserDefaults.standard.set(data, forKey: "trackedPodcastJobs")
    }
}

private extension JSONValue {
    var queryStringValue: String {
        switch self {
        case .string(let value):
            return value
        case .number(let value):
            return String(value)
        case .bool(let value):
            return value ? "true" : "false"
        case .null:
            return ""
        case .object, .array:
            return displayText
        }
    }
}

extension BridgeAPIError: LocalizedError {
    var errorDescription: String? {
        "\(code): \(message)"
    }
}
