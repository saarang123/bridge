import SwiftUI

struct JSONValueView: View {
    let value: JSONValue

    var body: some View {
        switch value {
        case .string(let string):
            Text(string)
        case .number(let number):
            Text(String(number))
        case .bool(let bool):
            Text(bool ? "true" : "false")
        case .null:
            Text("null")
                .foregroundStyle(.secondary)
        case .array(let values):
            if values.isEmpty {
                Text("Empty")
                    .foregroundStyle(.secondary)
            } else {
                ForEach(Array(values.enumerated()), id: \.offset) { _, item in
                    JSONValueView(value: item)
                        .padding(.vertical, 4)
                }
            }
        case .object(let object):
            VStack(alignment: .leading, spacing: 8) {
                if let title = object["title"]?.displayText {
                    Text(title)
                        .font(.headline)
                }

                ForEach(object.keys.sorted(), id: \.self) { key in
                    if key != "title", let value = object[key] {
                        LabeledContent(label(for: key), value: value.displayText)
                            .font(.subheadline)
                    }
                }
            }
            .padding(.vertical, 3)
        }
    }

    private func label(for key: String) -> String {
        key.replacingOccurrences(of: "_", with: " ").capitalized
    }
}
