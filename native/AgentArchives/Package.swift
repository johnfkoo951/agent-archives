// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "AgentArchives",
    platforms: [
        .macOS(.v14)
    ],
    products: [
        .executable(name: "AgentArchives", targets: ["AgentArchives"])
    ],
    targets: [
        .executableTarget(
            name: "AgentArchives",
            path: "Sources"
        )
    ]
)
