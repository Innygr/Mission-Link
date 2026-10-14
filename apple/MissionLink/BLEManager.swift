import Foundation
import Combine
import CoreBluetooth

@MainActor
final class BLEManager: NSObject, ObservableObject {
    // Must match the firmware GATT UUIDs in src/main.cpp.
    static let serviceUUID = CBUUID(string: "3F4A0001-7C2E-4A5B-9D11-5B7D6E100001")
    static let rxUUID = CBUUID(string: "3F4A0002-7C2E-4A5B-9D11-5B7D6E100001")
    static let txUUID = CBUUID(string: "3F4A0003-7C2E-4A5B-9D11-5B7D6E100001")

    @Published private(set) var bluetoothState = "Starting Bluetooth…"
    @Published private(set) var isConnected = false
    @Published private(set) var discoveredNames: [UUID: String] = [:]
    @Published private(set) var lines: [String] = ["MissionLink iOS ready. RF remains disabled in the current firmware."]
    @Published private(set) var selectedName = "No node selected"
    @Published private(set) var firmwareVersion = "Unknown"
    @Published private(set) var rfEnabled = false
    @Published private(set) var knownNodeCount: Int? = nil

    private var central: CBCentralManager!
    private var peripherals: [UUID: CBPeripheral] = [:]
    private var activePeripheral: CBPeripheral?
    private var rxCharacteristic: CBCharacteristic?
    private var txCharacteristic: CBCharacteristic?

    override init() {
        super.init()
        central = CBCentralManager(delegate: self, queue: .main)
    }

    func scan() {
        guard central.state == .poweredOn else {
            append("Bluetooth is not ready: \(bluetoothState)")
            return
        }
        discoveredNames.removeAll()
        peripherals.removeAll()
        append("Scanning for MissionLink nodes…")
        central.scanForPeripherals(withServices: [Self.serviceUUID], options: [CBCentralManagerScanOptionAllowDuplicatesKey: false])
    }

    func connect(id: UUID) {
        guard let peripheral = peripherals[id] else { return }
        central.stopScan()
        activePeripheral = peripheral
        selectedName = discoveredNames[id] ?? peripheral.name ?? "MissionLink"
        peripheral.delegate = self
        central.connect(peripheral, options: nil)
    }

    func disconnect() {
        if let activePeripheral { central.cancelPeripheralConnection(activePeripheral) }
    }

    func send(_ rawCommand: String) {
        guard let peripheral = activePeripheral,
              let characteristic = rxCharacteristic,
              isConnected else {
            append("Connect to a node before sending commands.")
            return
        }
        let command = rawCommand.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !command.isEmpty else { return }
        guard let data = command.data(using: .utf8), data.count <= 180 else {
            append("Command is empty or too long.")
            return
        }
        let type: CBCharacteristicWriteType = characteristic.properties.contains(.write) ? .withResponse : .withoutResponse
        peripheral.writeValue(data, for: characteristic, type: type)
        append("> \(command)")
    }

    private func append(_ line: String) {
        lines.append(line)
        if lines.count > 200 { lines.removeFirst(lines.count - 200) }
    }
}

extension BLEManager: CBCentralManagerDelegate {
    func centralManagerDidUpdateState(_ central: CBCentralManager) {
        switch central.state {
        case .poweredOn: bluetoothState = "Bluetooth ready"
        case .poweredOff: bluetoothState = "Bluetooth is off"
        case .unauthorized: bluetoothState = "Bluetooth permission denied"
        case .unsupported: bluetoothState = "Bluetooth LE unavailable"
        case .resetting: bluetoothState = "Bluetooth resetting"
        case .unknown: bluetoothState = "Bluetooth state unknown"
        @unknown default: bluetoothState = "Unknown Bluetooth state"
        }
    }

    func centralManager(_ central: CBCentralManager, didDiscover peripheral: CBPeripheral, advertisementData: [String: Any], rssi RSSI: NSNumber) {
        peripherals[peripheral.identifier] = peripheral
        discoveredNames[peripheral.identifier] = peripheral.name ?? (advertisementData[CBAdvertisementDataLocalNameKey] as? String) ?? "MissionLink Node"
    }

    func centralManager(_ central: CBCentralManager, didConnect peripheral: CBPeripheral) {
        isConnected = true
        activePeripheral = peripheral
        peripheral.delegate = self
        append("Connected to \(peripheral.name ?? "MissionLink"). Discovering services…")
        peripheral.discoverServices([Self.serviceUUID])
    }

    func centralManager(_ central: CBCentralManager, didFailToConnect peripheral: CBPeripheral, error: Error?) {
        isConnected = false
        append("Connection failed: \(error?.localizedDescription ?? "unknown error")")
    }

    func centralManager(_ central: CBCentralManager, didDisconnectPeripheral peripheral: CBPeripheral, error: Error?) {
        isConnected = false
        rxCharacteristic = nil
        txCharacteristic = nil
        activePeripheral = nil
        append("Disconnected.")
        if let error { append(error.localizedDescription) }
    }
}

extension BLEManager: CBPeripheralDelegate {
    func peripheral(_ peripheral: CBPeripheral, didDiscoverServices error: Error?) {
        if let error { append("Service discovery failed: \(error.localizedDescription)"); return }
        peripheral.services?.forEach { peripheral.discoverCharacteristics([Self.rxUUID, Self.txUUID], for: $0) }
    }

    func peripheral(_ peripheral: CBPeripheral, didDiscoverCharacteristicsFor service: CBService, error: Error?) {
        if let error { append("Characteristic discovery failed: \(error.localizedDescription)"); return }
        for characteristic in service.characteristics ?? [] {
            if characteristic.uuid == Self.rxUUID { rxCharacteristic = characteristic }
            if characteristic.uuid == Self.txUUID {
                txCharacteristic = characteristic
                peripheral.setNotifyValue(true, for: characteristic)
                peripheral.readValue(for: characteristic)
            }
        }
        if rxCharacteristic != nil && txCharacteristic != nil { append("MissionLink command channel ready.") }
    }

    func peripheral(_ peripheral: CBPeripheral, didUpdateValueFor characteristic: CBCharacteristic, error: Error?) {
        if let error { append("Read/notify failed: \(error.localizedDescription)"); return }
        guard let data = characteristic.value, let text = String(data: data, encoding: .utf8) else { return }
        text.split(whereSeparator: \.isNewline).forEach { handleFirmwareLine(String($0)) }
    }

    private func handleFirmwareLine(_ line: String) {
        guard let data = line.data(using: .utf8),
              let event = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let type = event["type"] as? String else {
            append(line)
            return
        }
        switch type {
        case "status", "ready", "boot":
            if let version = event["firmware"] as? String { firmwareVersion = version }
            if let enabled = event["rfEnabled"] as? Bool { rfEnabled = enabled }
            append("Firmware \(firmwareVersion) · RF \(rfEnabled ? "enabled" : "disabled")")
        case "nodes":
            if let items = event["items"] as? [Any] { knownNodeCount = items.count }
            append("Node discovery is not implemented in this firmware yet.")
        case "error":
            append("Error [\(event["code"] as? String ?? "unknown")]: \(event["message"] as? String ?? "Unknown error")")
        case "help":
            append("Firmware command list received.")
        default:
            append(line)
        }
    }

    func peripheral(_ peripheral: CBPeripheral, didWriteValueFor characteristic: CBCharacteristic, error: Error?) {
        if let error { append("Write failed: \(error.localizedDescription)") }
    }
}