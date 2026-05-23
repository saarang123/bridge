import Foundation

enum MockBridgeData {
    static let podcastActions = [
        BridgeAction(
            name: "generate_episode",
            title: "Generate Episode",
            description: "Start podcast generation.",
            uiKind: "form",
            method: "POST",
            idempotent: false,
            confirm: false,
            timeoutSeconds: nil,
            inputSchema: JSONSchema(
                type: "object",
                properties: ["source_uri": JSONSchema.string],
                required: ["source_uri"],
                enumValues: nil,
                items: nil,
                nullable: nil,
                title: nil,
                description: nil,
                defaultValue: nil
            ),
            outputSchema: JSONSchema.string
        ),
        BridgeAction(
            name: "list_sources",
            title: "List Sources",
            description: "List known source documents.",
            uiKind: "list",
            method: "GET",
            idempotent: true,
            confirm: false,
            timeoutSeconds: nil,
            inputSchema: JSONSchema.emptyObject,
            outputSchema: JSONSchema.arrayOfObjects
        ),
        BridgeAction(
            name: "list_episodes",
            title: "List Episodes",
            description: "List generated episodes.",
            uiKind: "list",
            method: "GET",
            idempotent: true,
            confirm: false,
            timeoutSeconds: nil,
            inputSchema: JSONSchema.emptyObject,
            outputSchema: JSONSchema.arrayOfObjects
        ),
    ]

    static var apps: [MiniApp] {
        [
            MiniApp(
                name: "podcast",
                title: "Podcast This",
                icon: "headphones",
                description: "Generate narrated podcast episodes from documents and links.",
                version: "0.1.0",
                actions: podcastActions
            )
        ]
    }

    static var activities: [Activity] {
        [
            Activity(
                id: "act_mock_001",
                kind: "job",
                app: "podcast",
                title: "Generate: transformers.md",
                status: "running",
                phase: "TTS",
                summary: "Rendering section audio.",
                createdAt: "2026-05-22T20:00:00Z",
                updatedAt: "2026-05-22T20:04:00Z",
                actions: ["cancel"],
                detailURL: nil
            )
        ]
    }

    static func invoke(app: MiniApp, action: BridgeAction, body: [String: JSONValue]) -> JSONValue? {
        switch action.name {
        case "list_sources":
            return decodeJSONValue("""
            [
              {
                "title": "Backpropagation Notes",
                "source_uri": "/example/docs/backprop.md",
                "kind": "markdown"
              },
              {
                "title": "Transformer Architecture",
                "source_uri": "/example/docs/transformers.md",
                "kind": "markdown"
              }
            ]
            """)
        case "list_episodes":
            return decodeJSONValue("""
            [
              {
                "title": "Example Episode",
                "status": "published",
                "audio_url": "https://example.invalid/audio/example.mp3"
              }
            ]
            """)
        case "generate_episode":
            return .string("act_mock_002")
        default:
            return .string("ok")
        }
    }

    private static func decodeJSONValue(_ json: String) -> JSONValue? {
        guard let data = json.data(using: .utf8) else {
            return nil
        }
        return try? JSONDecoder().decode(JSONValue.self, from: data)
    }
}

extension JSONSchema {
    static let string = JSONSchema(
        type: "string",
        properties: nil,
        required: nil,
        enumValues: nil,
        items: nil,
        nullable: nil,
        title: nil,
        description: nil,
        defaultValue: nil
    )

    static let emptyObject = JSONSchema(
        type: "object",
        properties: [:],
        required: nil,
        enumValues: nil,
        items: nil,
        nullable: nil,
        title: nil,
        description: nil,
        defaultValue: nil
    )

    static let arrayOfObjects = JSONSchema(
        type: "array",
        properties: nil,
        required: nil,
        enumValues: nil,
        items: JSONSchema(
            type: "object",
            properties: nil,
            required: nil,
            enumValues: nil,
            items: nil,
            nullable: nil,
            title: nil,
            description: nil,
            defaultValue: nil
        ),
        nullable: nil,
        title: nil,
        description: nil,
        defaultValue: nil
    )
}
