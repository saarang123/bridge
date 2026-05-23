import Foundation

struct AppsResponse: Decodable {
    let apps: [MiniApp]
}

struct MiniApp: Decodable, Identifiable {
    let name: String
    let title: String
    let icon: String
    let description: String
    let version: String
    let actions: [BridgeAction]

    var id: String { name }
}

struct BridgeAction: Decodable, Identifiable {
    let name: String
    let title: String
    let description: String
    let uiKind: String
    let method: String
    let idempotent: Bool
    let confirm: Bool
    let timeoutSeconds: Double?
    let inputSchema: JSONSchema
    let outputSchema: JSONSchema

    var id: String { name }

    enum CodingKeys: String, CodingKey {
        case name
        case title
        case description
        case uiKind = "ui_kind"
        case method
        case idempotent
        case confirm
        case timeoutSeconds = "timeout_s"
        case inputSchema = "input_schema"
        case outputSchema = "output_schema"
    }
}

final class JSONSchema: Decodable {
    let type: String?
    let properties: [String: JSONSchema]?
    let required: [String]?
    let enumValues: [JSONValue]?
    let items: JSONSchema?
    let nullable: Bool?
    let title: String?
    let description: String?
    let defaultValue: JSONValue?

    init(
        type: String?,
        properties: [String: JSONSchema]?,
        required: [String]?,
        enumValues: [JSONValue]?,
        items: JSONSchema?,
        nullable: Bool?,
        title: String?,
        description: String?,
        defaultValue: JSONValue?
    ) {
        self.type = type
        self.properties = properties
        self.required = required
        self.enumValues = enumValues
        self.items = items
        self.nullable = nullable
        self.title = title
        self.description = description
        self.defaultValue = defaultValue
    }

    enum CodingKeys: String, CodingKey {
        case type
        case properties
        case required
        case enumValues = "enum"
        case items
        case nullable
        case title
        case description
        case defaultValue = "default"
    }
}

enum JSONValue: Codable, Hashable {
    case string(String)
    case number(Double)
    case bool(Bool)
    case object([String: JSONValue])
    case array([JSONValue])
    case null

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if container.decodeNil() {
            self = .null
        } else if let value = try? container.decode(Bool.self) {
            self = .bool(value)
        } else if let value = try? container.decode(Double.self) {
            self = .number(value)
        } else if let value = try? container.decode(String.self) {
            self = .string(value)
        } else if let value = try? container.decode([JSONValue].self) {
            self = .array(value)
        } else {
            self = .object(try container.decode([String: JSONValue].self))
        }
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        switch self {
        case .string(let value):
            try container.encode(value)
        case .number(let value):
            try container.encode(value)
        case .bool(let value):
            try container.encode(value)
        case .object(let value):
            try container.encode(value)
        case .array(let value):
            try container.encode(value)
        case .null:
            try container.encodeNil()
        }
    }

    var displayText: String {
        switch self {
        case .string(let value):
            return value
        case .number(let value):
            return String(value)
        case .bool(let value):
            return value ? "true" : "false"
        case .object(let value):
            return "\(value.count) fields"
        case .array(let value):
            return "\(value.count) items"
        case .null:
            return "null"
        }
    }

    var stringValue: String? {
        if case .string(let value) = self {
            return value
        }
        return nil
    }
}

struct ActionEnvelope: Decodable {
    let ok: Bool
    let data: JSONValue?
    let error: BridgeAPIError?
}

struct BridgeAPIError: Decodable, Error {
    let code: String
    let message: String
}

struct ActivitiesResponse: Decodable {
    let activities: [Activity]
}

struct Activity: Decodable, Identifiable {
    let id: String
    let kind: String
    let app: String
    let title: String
    let status: String
    let phase: String
    let summary: String
    let createdAt: String
    let updatedAt: String
    let actions: [String]
    let detailURL: String?

    enum CodingKeys: String, CodingKey {
        case id
        case kind
        case app
        case title
        case status
        case phase
        case summary
        case createdAt = "created_at"
        case updatedAt = "updated_at"
        case actions
        case detailURL = "detail_url"
    }
}

struct TrackedPodcastJob: Codable, Identifiable {
    let jobID: String
    let sourceURI: String
    var status: String
    var phase: String
    var message: String
    var audioURL: String?
    var feedURL: String?
    let createdAt: String
    var updatedAt: String

    var id: String { jobID }

    enum CodingKeys: String, CodingKey {
        case jobID = "job_id"
        case sourceURI = "source_uri"
        case status
        case phase
        case message
        case audioURL = "audio_url"
        case feedURL = "feed_url"
        case createdAt = "created_at"
        case updatedAt = "updated_at"
    }

    var activity: Activity {
        Activity(
            id: "podcast-job-\(jobID)",
            kind: "job",
            app: "podcast",
            title: "Generate: \(sourceURI.split(separator: "/").last.map(String.init) ?? sourceURI)",
            status: status,
            phase: phase,
            summary: message.isEmpty ? sourceURI : message,
            createdAt: createdAt,
            updatedAt: updatedAt,
            actions: isTerminal ? [] : ["poll"],
            detailURL: audioURL ?? feedURL
        )
    }

    var isTerminal: Bool {
        status == "complete" || status == "failed" || status == "cancelled"
    }
}
