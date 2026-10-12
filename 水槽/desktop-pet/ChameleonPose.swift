// Pose shared by the placeholder drawing and, later, the specimen model.
// Screen-facing yaw: 0 looks right, π looks left. Pitch lifts the nose when climbing.

import CoreGraphics

struct ChameleonFoot {
  var position: CGPoint
  var planted: Bool
}

struct ChameleonPose {
  /// How far the head reaches from the feet, in the direction the body faces.
  static let headReach: CGFloat = 78
  /// How far the tail reaches the other way. A curled tail is shorter.
  static let tailReach: CGFloat = 88
  static let curledTailReach: CGFloat = 46
  /// Foot homes relative to the body anchor, in the facing-right drawing.
  /// Pairs (0, 3) and (1, 2) step together.
  static let homes: [CGPoint] = [
    CGPoint(x: -24, y: 0),
    CGPoint(x: -2, y: 0),
    CGPoint(x: 16, y: 0),
    CGPoint(x: 36, y: 0),
  ]

  var body = CGPoint(x: 110, y: 26)
  var yaw: CGFloat = 0
  var pitch: CGFloat = 0
  var feet: [ChameleonFoot] = []
  var eyeLeft = CGPoint(x: 160, y: 80)
  var eyeRight = CGPoint(x: 180, y: 90)
  var tailCurl: CGFloat = 0.15
  var sway: CGFloat = 0

  func tailReachNow() -> CGFloat {
    tailCurl > 0.5 ? Self.curledTailReach : Self.tailReach
  }
}
