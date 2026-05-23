import SwiftUI

@main
struct BridgeApp: App {
    @StateObject private var client = BridgeClient()

    var body: some Scene {
        WindowGroup {
            RootTabView()
                .environmentObject(client)
        }
    }
}
