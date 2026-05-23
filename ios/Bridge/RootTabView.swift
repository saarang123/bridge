import SwiftUI

struct RootTabView: View {
    @EnvironmentObject private var client: BridgeClient

    var body: some View {
        TabView {
            AppsView()
                .tabItem {
                    Label("Apps", systemImage: "square.grid.2x2")
                }

            ActiveView()
                .tabItem {
                    Label("Active", systemImage: "waveform.path.ecg")
                }

            SettingsView()
                .tabItem {
                    Label("Settings", systemImage: "gearshape")
                }
        }
        .task {
            await client.refresh()
        }
    }
}
