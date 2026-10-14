import SwiftUI

struct ContentView: View {
    @StateObject private var ble = BLEManager()
    @State private var command = "status"

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    VStack(alignment: .leading, spacing: 6) {
                        Text("MISSIONLINK / IOS").font(.caption.weight(.bold)).tracking(2).foregroundStyle(.teal)
                        Text("Your network.\nIn your hands.").font(.system(size: 34, weight: .bold, design: .rounded))
                        Text("Local-first radio control. No internet required for a nearby BLE connection.")
                            .foregroundStyle(.secondary)
                    }
                    statusCard
                    VStack(alignment: .leading, spacing: 10) {
                        HStack {
                            Text("Nearby nodes").font(.headline)
                            Spacer()
                            Button("Scan") { ble.scan() }.buttonStyle(.borderedProminent).tint(.green)
                        }
                        if ble.discoveredNames.isEmpty {
                            Text("Tap Scan to look for MissionLink radios.").font(.subheadline).foregroundStyle(.secondary)
                        } else {
                            ForEach(ble.discoveredNames.keys.sorted(by: { $0.uuidString < $1.uuidString }), id: \.self) { id in
                                HStack {
                                    VStack(alignment: .leading) {
                                        Text(ble.discoveredNames[id] ?? "MissionLink")
                                        Text(id.uuidString.prefix(8)).font(.caption2).foregroundStyle(.secondary)
                                    }
                                    Spacer()
                                    Button("Connect") { ble.connect(id: id) }.buttonStyle(.bordered)
                                }.padding(.vertical, 4)
                            }
                        }
                    }.cardStyle()
                    VStack(alignment: .leading, spacing: 10) {
                        Text("Command console").font(.headline)
                        HStack {
                            TextField("status", text: $command).textInputAutocapitalization(.never).autocorrectionDisabled().font(.system(.body, design: .monospaced))
                            Button("Send") { ble.send(command) }.buttonStyle(.borderedProminent).tint(.green)
                        }
                        HStack(spacing: 8) {
                            commandChip("help")
                            commandChip("status")
                            commandChip("nodes")
                        }
                    }.cardStyle()
                    VStack(alignment: .leading, spacing: 10) {
                        HStack {
                            Text("Activity").font(.headline)
                            Spacer()
                            Button("Disconnect") { ble.disconnect() }.disabled(!ble.isConnected).font(.caption)
                        }
                        ForEach(Array(ble.lines.suffix(60).enumerated()), id: \.offset) { _, line in
                            Text(line).font(.system(.caption, design: .monospaced)).frame(maxWidth: .infinity, alignment: .leading).textSelection(.enabled)
                        }
                    }.cardStyle()
                    Text("RF is disabled in the current firmware. This app is a starter UI, not yet a production messaging client.")
                        .font(.footnote).foregroundStyle(.secondary)
                }.padding(18)
            }
            .background(Color(red: 0.06, green: 0.09, blue: 0.11))
            .navigationBarTitleDisplayMode(.inline)
            .toolbar { ToolbarItem(placement: .principal) { Text("MissionLink").font(.headline) } }
        }
        .preferredColorScheme(.dark)
    }

    private var statusCard: some View {
        VStack(alignment: .leading, spacing: 8) {
            Label(ble.isConnected ? "Connected" : "Not connected", systemImage: ble.isConnected ? "checkmark.circle.fill" : "antenna.radiowaves.left.and.right")
                .font(.headline).foregroundStyle(ble.isConnected ? .green : .secondary)
            Text(ble.bluetoothState).font(.subheadline)
            Text("Selected: \(ble.selectedName)").font(.caption).foregroundStyle(.secondary)
            Text("Firmware: \(ble.firmwareVersion)").font(.caption).foregroundStyle(.secondary)
            Text("Known nodes: \(ble.knownNodeCount.map(String.init) ?? "—")").font(.caption).foregroundStyle(.secondary)
            Text("Radio link: not ready").font(.caption.weight(.semibold)).foregroundStyle(.orange)
        }.frame(maxWidth: .infinity, alignment: .leading).cardStyle()
    }

    private func commandChip(_ value: String) -> some View {
        Button(value) { command = value }.buttonStyle(.bordered).font(.system(.caption, design: .monospaced))
    }
}

private extension View {
    func cardStyle() -> some View {
        self.padding(15)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(Color.white.opacity(0.055), in: RoundedRectangle(cornerRadius: 16))
            .overlay(RoundedRectangle(cornerRadius: 16).stroke(Color.white.opacity(0.09), lineWidth: 1))
    }
}