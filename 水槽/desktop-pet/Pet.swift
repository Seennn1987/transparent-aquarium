// A placeholder chameleon that walks on the Mac desktop.
//
// The wallpaper agent sits at the desktop-window level, under the icons. This pet sits
// one level above the desktop icons and well under ordinary app windows, in a small
// transparent window that follows its feet. Clicks pass through to the Finder.
//
// The drawing is a flat green stand-in. The transparent-specimen model is not part of
// this app.

import Cocoa

enum PetMetrics {
  static let windowSize = NSSize(width: 260, height: 190)
  /// Feet, in the pet window. The window is placed so this point lies on the desktop.
  static let anchor = NSPoint(x: 110, y: 26)
  /// Cruise speed. Starts and stops are slower than this.
  static let cruise: CGFloat = 36
  static let logPath = "/tmp/desktop-pet.log"
}

enum Act: Equatable {
  case walk
  case hold(until: TimeInterval)
  case look(until: TimeInterval)
  case sit(until: TimeInterval)
}

/// One foot in the gait. Planted feet keep their world position.
private struct FootSim {
  var world: CGPoint
  var planted: Bool
  var from: CGPoint
  var to: CGPoint
  var swing: CGFloat
}

/// A branch the chameleon follows. Open wallpaper is only the gap between branches.
enum Branch: Equatable {
  case column(up: Bool)
  case dock(right: Bool)
  case side(left: Bool, up: Bool)
}

/// A borderless window that keeps the frame it is given, including at the screen edge.
final class PlainWindow: NSWindow {
  override func constrainFrameRect(_ rect: NSRect, to screen: NSScreen?) -> NSRect { rect }
  override var canBecomeKey: Bool { false }
  override var canBecomeMain: Bool { false }
}

/// Flat green chameleon. The body yaws in the ground plane; the feet stay where they were planted.
final class PetView: NSView {
  var pose = ChameleonPose()

  override var isOpaque: Bool { false }

  override func draw(_ dirtyRect: NSRect) {
    NSColor.clear.setFill()
    dirtyRect.fill(using: .copy)
    guard let ctx = NSGraphicsContext.current?.cgContext else { return }
    let anchor = PetMetrics.anchor
    let shift = CGPoint(x: pose.body.x - anchor.x, y: pose.body.y - anchor.y)
    let dark = NSColor(calibratedRed: 0.13, green: 0.28, blue: 0.16, alpha: 1)

    ctx.saveGState()
    ctx.translateBy(x: shift.x, y: shift.y)
    ctx.translateBy(x: anchor.x, y: anchor.y)
    ctx.rotate(by: pose.pitch * 0.45)
    ctx.scaleBy(x: cos(pose.yaw), y: 1)
    ctx.translateBy(x: -anchor.x, y: -anchor.y)
    drawBody()
    let left = bodyPoint(pose.eyeLeft)
    let right = bodyPoint(pose.eyeRight)
    eye(center: NSPoint(x: 150, y: 80), aim: left, radius: 6.5)
    eye(center: NSPoint(x: 166, y: 84), aim: right, radius: 5.5)
    ctx.restoreGState()

    let hips = [
      NSPoint(x: 96, y: 52), NSPoint(x: 110, y: 50), NSPoint(x: 128, y: 52), NSPoint(x: 140, y: 50),
    ]
    if pose.feet.count == hips.count {
      for (hip, foot) in zip(hips, pose.feet) {
        let joint = hipView(hip)
        let viewHip = CGPoint(x: joint.x + shift.x, y: joint.y + shift.y)
        limb(from: viewHip, to: foot.position, planted: foot.planted, dark: dark)
      }
    }
  }

  private func drawBody() {
    let anchor = PetMetrics.anchor
    let body = NSColor(calibratedRed: 0.30, green: 0.58, blue: 0.34, alpha: 1)
    let belly = NSColor(calibratedRed: 0.74, green: 0.84, blue: 0.52, alpha: 1)
    let dark = NSColor(calibratedRed: 0.13, green: 0.28, blue: 0.16, alpha: 1)
    let curl = pose.tailCurl
    let wave = pose.sway

    NSColor(calibratedWhite: 0, alpha: 0.16).setFill()
    NSBezierPath(ovalIn: NSRect(x: anchor.x - 34, y: anchor.y - 5, width: 68, height: 10)).fill()

    let tail = NSBezierPath()
    tail.move(to: NSPoint(x: 86, y: 58))
    tail.curve(
      to: NSPoint(x: 34 + curl * 28, y: 70 + curl * 16),
      controlPoint1: NSPoint(x: 48, y: 28 + wave + curl * 18),
      controlPoint2: NSPoint(x: 16 + curl * 24, y: 46 + curl * 10))
    stroke(tail, width: 8, color: body)
    stroke(tail, width: 1.5, color: dark)

    let torso = NSBezierPath(ovalIn: NSRect(x: 78, y: 46, width: 76, height: 34))
    body.setFill()
    torso.fill()
    belly.setFill()
    NSBezierPath(ovalIn: NSRect(x: 96, y: 46, width: 46, height: 16)).fill()
    stroke(torso, width: 1.5, color: dark)

    let crest = NSBezierPath()
    crest.move(to: NSPoint(x: 96, y: 74))
    crest.line(to: NSPoint(x: 108, y: 96))
    crest.line(to: NSPoint(x: 122, y: 76))
    crest.line(to: NSPoint(x: 136, y: 102))
    crest.line(to: NSPoint(x: 150, y: 78))
    stroke(crest, width: 2, color: dark)

    let head = NSBezierPath(ovalIn: NSRect(x: 140, y: 58, width: 36, height: 32))
    body.setFill()
    head.fill()
    stroke(head, width: 1.5, color: dark)
    let snout = NSBezierPath(ovalIn: NSRect(x: 166, y: 62, width: 22, height: 12))
    body.setFill()
    snout.fill()
    stroke(snout, width: 1.5, color: dark)
  }

  private func hipView(_ local: CGPoint) -> CGPoint {
    let anchor = PetMetrics.anchor
    let dx = local.x - anchor.x
    return CGPoint(
      x: anchor.x + dx * cos(pose.yaw),
      y: anchor.y + (local.y - anchor.y) + dx * sin(pose.pitch) * 0.35)
  }

  /// Eye aims are in window space. The head is drawn in the shifted, yaw-scaled space.
  private func bodyPoint(_ viewPoint: CGPoint) -> CGPoint {
    let anchor = PetMetrics.anchor
    let art = CGPoint(
      x: viewPoint.x - (pose.body.x - anchor.x),
      y: viewPoint.y - (pose.body.y - anchor.y))
    let scale = cos(pose.yaw)
    let denom = abs(scale) < 0.2 ? (scale < 0 ? -0.2 : 0.2) : scale
    return CGPoint(x: anchor.x + (art.x - anchor.x) / denom, y: art.y)
  }

  private func limb(from hip: CGPoint, to foot: CGPoint, planted: Bool, dark: NSColor) {
    let knee = NSPoint(x: (hip.x + foot.x) / 2, y: max(hip.y, foot.y) - 12)
    let path = NSBezierPath()
    path.move(to: hip)
    path.line(to: knee)
    path.line(to: foot)
    stroke(path, width: planted ? 3.5 : 2.4, color: dark)
    let toes = NSBezierPath()
    toes.move(to: foot)
    toes.line(to: NSPoint(x: foot.x - 6, y: foot.y - 3))
    toes.move(to: foot)
    toes.line(to: NSPoint(x: foot.x + 5, y: foot.y - 3))
    stroke(toes, width: 2, color: dark)
  }

  private func eye(center: NSPoint, aim: NSPoint, radius: CGFloat) {
    let dx = aim.x - center.x
    let dy = aim.y - center.y
    let len = max(hypot(dx, dy), 0.001)
    let reach = radius * 0.42
    let pupil = NSPoint(x: center.x + dx / len * reach, y: center.y + dy / len * reach)
    NSColor(calibratedRed: 0.94, green: 0.96, blue: 0.86, alpha: 1).setFill()
    NSBezierPath(ovalIn: NSRect(
      x: center.x - radius, y: center.y - radius, width: radius * 2, height: radius * 2
    )).fill()
    NSColor(calibratedRed: 0.1, green: 0.14, blue: 0.1, alpha: 1).setFill()
    NSBezierPath(ovalIn: NSRect(x: pupil.x - 2.2, y: pupil.y - 2.2, width: 4.4, height: 4.4)).fill()
  }

  private func stroke(_ path: NSBezierPath, width: CGFloat, color: NSColor) {
    color.setStroke()
    path.lineWidth = width
    path.lineCapStyle = .round
    path.lineJoinStyle = .round
    path.stroke()
  }
}

/// Icon rectangles and the Dock's top edge, in the debug window's own coordinates.
final class FeetView: NSView {
  var icons: [NSRect] = []
  var dockY: CGFloat?

  override var isOpaque: Bool { false }

  override func draw(_ dirtyRect: NSRect) {
    NSColor.clear.setFill()
    dirtyRect.fill(using: .copy)
    let green = NSColor(calibratedRed: 0.2, green: 0.85, blue: 0.4, alpha: 0.95)
    green.setStroke()
    for icon in icons {
      let path = NSBezierPath(rect: icon)
      path.lineWidth = 1.5
      path.stroke()
    }
    if let dockY {
      NSColor(calibratedRed: 0.95, green: 0.55, blue: 0.15, alpha: 0.95).setStroke()
      let line = NSBezierPath()
      line.move(to: NSPoint(x: 0, y: dockY))
      line.line(to: NSPoint(x: bounds.width, y: dockY))
      line.lineWidth = 2
      line.stroke()
    }
  }
}

final class PetApp: NSObject, NSApplicationDelegate, NSMenuDelegate {
  private let petView = PetView(frame: NSRect(origin: .zero, size: PetMetrics.windowSize))
  private let feetView = FeetView(frame: .zero)
  private var petWindow: PlainWindow?
  private var feetWindow: PlainWindow?
  private var icons: [NSRect] = []
  private var iconSize: CGFloat = 64
  private var skippedIcons = 0
  private var iconError: String?
  private var feet = NSPoint.zero
  private var destination = NSPoint.zero
  private var waypoints: [NSPoint] = []
  private var act: Act = .walk
  private var branch: Branch = .side(left: false, up: true)
  private var walked: CGFloat = 0
  private var pauseEvery: CGFloat = 110
  private var pendingFacing: Bool?
  private var gazeScreen: NSPoint?
  private var swayX: CGFloat = 0
  private var swayY: CGFloat = 0
  private var didJoinColumn = false
  private var facingRight = true
  private var yaw: CGFloat = 0
  private var yawTarget: CGFloat = 0
  private var pitch: CGFloat = 0
  private var feetSim: [FootSim] = []
  private var stepPair = 0
  private var pairBusy = false
  private var climbAnnounced = false
  private var phase: CGFloat = 0
  private var paused = false
  private var showFeet = false
  private var lastTick = Date()
  private var lastPulse = Date.distantPast
  private var askedFinder = false
  private var refreshingIcons = false
  private var wrotePreview = false
  private var loggedIconCount: Int?
  private let iconQueue = DispatchQueue(label: "desktop-pet.icons")
  private var moveTimer: Timer?
  private var iconTimer: Timer?
  private var status: NSStatusItem?
  private let infoItem = NSMenuItem()
  private let feetItem = NSMenuItem()
  private let pauseItem = NSMenuItem()

  /// Finder `desktop position` is the icon's top-left. Origin is the top-left of the
  /// primary screen, and y grows downward. Returns an AppKit rect (origin bottom-left).
  static func iconRect(fx: CGFloat, fy: CGFloat, size: CGFloat, screen: NSScreen) -> NSRect {
    let x = screen.frame.minX + fx
    let top = screen.frame.maxY - fy
    return NSRect(x: x, y: top - size, width: size, height: size)
  }

  func applicationDidFinishLaunching(_ notification: Notification) {
    FileManager.default.createFile(atPath: PetMetrics.logPath, contents: Data())
    showFeet = CommandLine.arguments.contains("--feet")
    guard let screen = NSScreen.screens.first else {
      log("no screen")
      return
    }
    let iconLevel = Int(CGWindowLevelForKey(.desktopIconWindow))
    let normalLevel = Int(CGWindowLevelForKey(.normalWindow))
    let chosen = iconLevel + 1 < normalLevel ? iconLevel + 1 : iconLevel
    log("level \(chosen) (icons \(iconLevel), normal \(normalLevel))")
    log("screen \(rectText(screen.frame)) visible \(rectText(screen.visibleFrame))")

    let level = NSWindow.Level(rawValue: chosen)
    let pet = makeWindow(
      frame: NSRect(origin: .zero, size: PetMetrics.windowSize), level: level, view: petView)
    petWindow = pet

    let feet = makeWindow(frame: screen.frame, level: level, view: feetView)
    feetWindow = feet
    if !showFeet { feet.orderOut(nil) }

    let visible = screen.visibleFrame
    self.feet = NSPoint(x: visible.minX + ChameleonPose.headReach, y: visible.midY)
    plantAllFeet()
    startSide(left: true, up: true, on: screen, turning: false)
    place(on: screen)
    if showFeet { feet.orderFrontRegardless() }
    pet.orderFrontRegardless()
    log("pet window \(pet.windowNumber) ignoresMouse \(pet.ignoresMouseEvents)")
    addMenu()

    let move = Timer(timeInterval: 1.0 / 30.0, repeats: true) { [weak self] _ in self?.tick() }
    RunLoop.main.add(move, forMode: .common)
    moveTimer = move
    let icons = Timer(timeInterval: 5, repeats: true) { [weak self] _ in self?.refreshIcons() }
    icons.fireDate = Date().addingTimeInterval(0.6)
    RunLoop.main.add(icons, forMode: .common)
    iconTimer = icons

    NotificationCenter.default.addObserver(
      self, selector: #selector(screensChanged),
      name: NSApplication.didChangeScreenParametersNotification, object: nil)
  }

  private func makeWindow(frame: NSRect, level: NSWindow.Level, view: NSView) -> PlainWindow {
    let window = PlainWindow(
      contentRect: frame, styleMask: .borderless, backing: .buffered, defer: false)
    window.level = level
    window.collectionBehavior = [.canJoinAllSpaces, .stationary, .ignoresCycle]
    window.ignoresMouseEvents = true
    window.isOpaque = false
    window.hasShadow = false
    window.backgroundColor = .clear
    window.isReleasedWhenClosed = false
    window.canHide = false
    window.animationBehavior = .none
    window.contentView = view
    return window
  }

  private func addMenu() {
    let item = NSStatusBar.system.statusItem(withLength: NSStatusItem.squareLength)
    if let symbol = NSImage(systemSymbolName: "lizard", accessibilityDescription: "仮カメレオン") {
      symbol.isTemplate = true
      item.button?.image = symbol
    } else {
      item.button?.title = "カ"
    }
    item.button?.toolTip = "仮カメレオン"

    let menu = NSMenu()
    menu.autoenablesItems = false
    menu.delegate = self
    infoItem.isEnabled = false
    menu.addItem(infoItem)
    menu.addItem(.separator())
    feetItem.target = self
    feetItem.action = #selector(toggleFeet)
    menu.addItem(feetItem)
    pauseItem.target = self
    pauseItem.action = #selector(togglePause)
    menu.addItem(pauseItem)
    menu.addItem(.separator())
    let quit = NSMenuItem(title: "終了", action: #selector(quit), keyEquivalent: "q")
    quit.target = self
    menu.addItem(quit)
    item.menu = menu
    status = item
    if item.button?.window == nil || !item.isVisible {
      log("menu bar item did not appear")
    } else {
      log("menu ready")
    }
  }

  func menuNeedsUpdate(_ menu: NSMenu) {
    if let iconError, icons.isEmpty {
      infoItem.title = iconError
    } else if skippedIcons > 0 {
      infoItem.title = "\(modeLabel) · 乗れるアイコン \(icons.count) 個"
    } else {
      infoItem.title = "\(modeLabel) · アイコン \(icons.count) 個"
    }
    feetItem.title = showFeet ? "足場を隠す" : "足場を表示"
    pauseItem.title = paused ? "再開" : "一時停止"
  }

  private var modeLabel: String {
    if paused { return "停止中" }
    switch act {
    case .walk:
      switch branch {
      case .dock: return "Dock"
      case .column: return "アイコンへ"
      case .side: return "歩いている"
      }
    case .hold, .look: return "立ち止まっている"
    case .sit: return "アイコンの上"
    }
  }

  private var isStill: Bool {
    if case .walk = act { return false }
    return true
  }

  @objc private func toggleFeet() {
    showFeet.toggle()
    guard let screen = NSScreen.screens.first, let feetWindow, let petWindow else { return }
    if showFeet {
      feetWindow.setFrame(screen.frame, display: false)
      updateFeetView(on: screen)
      feetWindow.orderFrontRegardless()
      petWindow.orderFrontRegardless()
    } else {
      feetWindow.orderOut(nil)
    }
    log(showFeet ? "feet on" : "feet off")
  }

  @objc private func togglePause() {
    paused.toggle()
    log(paused ? "paused" : "resumed")
  }

  @objc private func quit() {
    NSApp.terminate(nil)
  }

  @objc private func screensChanged() {
    guard let screen = NSScreen.screens.first, let feetWindow else { return }
    feetWindow.setFrame(screen.frame, display: false)
    feetView.frame = NSRect(origin: .zero, size: screen.frame.size)
    updateFeetView(on: screen)
    log("screen \(rectText(screen.frame))")
  }

  private func tick() {
    guard let screen = NSScreen.screens.first else { return }
    let now = Date()
    let dt = min(0.05, now.timeIntervalSince(lastTick))
    lastTick = now
    let clock = now.timeIntervalSinceReferenceDate
    if !paused {
      switch act {
      case .sit(let until):
        phase += CGFloat(dt) * 0.8
        rock(clock)
        if clock >= until { afterSit(on: screen) }
      case .hold(let until):
        phase += CGFloat(dt) * 1.6
        rock(clock)
        if clock >= until {
          gazeScreen = nil
          act = .walk
          walked = 0
        }
      case .look(let until):
        phase += CGFloat(dt) * 0.7
        rock(clock)
        if clock >= until {
          if let pendingFacing { aimYaw(right: pendingFacing) }
          pendingFacing = nil
          gazeScreen = nil
          act = .walk
          walked = 0
        }
      case .walk:
        swayX = 0
        swayY = 0
        step(on: screen, dt: CGFloat(dt), clock: clock)
      }
    }
    updateYaw(CGFloat(dt))
    updateFeet(CGFloat(dt))
    keepBodyClear(on: screen)
    place(on: screen)
    if !wrotePreview {
      wrotePreview = true
      writePreview()
    }
    if now.timeIntervalSince(lastPulse) > 3 {
      lastPulse = now
      let planted = feetSim.filter(\.planted).count
      let body = bodyRect(at: feet, on: screen)
      let off = body.maxX > screen.frame.maxX + 1 || body.minX < screen.frame.minX - 1
      log(
        "at \(Int(feet.x)),\(Int(feet.y)) \(modeLabel) yaw \(Int(yaw * 180 / .pi)) planted \(planted)\(off ? " offscreen" : "")"
      )
    }
  }

  private func rock(_ clock: TimeInterval) {
    let amount = sin(CGFloat(clock) * 2.4) * 3.2
    switch branch {
    case .dock:
      swayX = 0
      swayY = amount
    default:
      swayX = amount
      swayY = 0
    }
  }

  private func step(on screen: NSScreen, dt: CGFloat, clock: TimeInterval) {
    if abs(yaw - yawTarget) > 0.28 { return }
    let dx = destination.x - feet.x
    let dy = destination.y - feet.y
    let dist = hypot(dx, dy)
    if dist < 2.5 {
      arrive(on: screen)
      return
    }
    if isClimbing {
      let lead = leadFootIndex
      let foot = feetSim.indices.contains(lead) ? feetSim[lead] : nil
      let reached = foot.map { $0.planted && hypot($0.world.x - destination.x, $0.world.y - destination.y) < 14 } ?? false
      if !reached {
        reachFoot(lead, to: destination)
        pitch = min(0.3, pitch + CGFloat(dt) * 0.7)
        if !climbAnnounced {
          climbAnnounced = true
          log("reach foot \(lead) before body")
        }
        return
      }
      if climbAnnounced {
        climbAnnounced = false
        log("foot down, body rises")
      }
    }
    pitch = max(0, pitch - CGFloat(dt) * 0.45)
    let remainRamp = min(1, dist / 36)
    let startRamp = min(1, max(0, walked) / 28)
    let pace = PetMetrics.cruise * (0.2 + 0.8 * min(remainRamp, startRamp))
    let move = min(dist, pace * dt)
    feet.x += dx / dist * move
    feet.y += dy / dist * move
    walked += move
    phase += move * 0.22
    if walked > pauseEvery, dist > 48 {
      pauseEvery = CGFloat.random(in: 80...140)
      walked = 0
      act = .hold(until: clock + Double.random(in: 0.7...1.6))
      logAct()
    }
  }

  private func arrive(on screen: NSScreen) {
    if !waypoints.isEmpty {
      let next = waypoints.removeFirst()
      setDestination(next, on: screen, turning: false)
      return
    }
    switch branch {
    case .column(let up):
      if nearPerch(on: screen) {
        aimYaw(right: wantsFaceRight(toward: feet, on: screen))
        act = .sit(until: Date().timeIntervalSinceReferenceDate + Double.random(in: 7...12))
        gazeScreen = nil
        logAct()
        return
      }
      followColumn(up: up, on: screen, turning: true)
    case .dock(let right):
      if right, !columnPerches(on: screen).isEmpty, Int.random(in: 0..<4) == 0 {
        followColumn(up: true, on: screen, turning: true)
        return
      }
      followDock(right: !right, on: screen, turning: true)
    case .side(let left, let up):
      if !left, !columnPerches(on: screen).isEmpty, Int.random(in: 0..<2) == 0 {
        followColumn(up: !up, on: screen, turning: true)
        return
      }
      if Int.random(in: 0..<5) == 0, dockTop(on: screen) != nil {
        followDock(right: left, on: screen, turning: true)
        return
      }
      startSide(left: left, up: !up, on: screen, turning: true)
    }
  }

  private func afterSit(on screen: NSScreen) {
    if Int.random(in: 0..<5) == 0, dockTop(on: screen) != nil {
      followDock(right: feet.x < screen.visibleFrame.midX, on: screen, turning: true)
      return
    }
    if case .column(let up) = branch {
      followColumn(up: up, on: screen, turning: false)
    } else {
      followColumn(up: true, on: screen, turning: false)
    }
  }

  /// One straight leg, then the other. Never a diagonal.
  /// Dropping to the Dock goes down first. Climbing an icon lines up underneath, then goes up.
  private func axis(from: NSPoint, to: NSPoint, verticalFirst: Bool) -> [NSPoint] {
    if abs(from.x - to.x) < 4 || abs(from.y - to.y) < 4 { return [to] }
    if verticalFirst { return [NSPoint(x: from.x, y: to.y), to] }
    return [NSPoint(x: to.x, y: from.y), to]
  }

  private func setDestination(
    _ point: NSPoint, on screen: NSScreen, turning: Bool, verticalFirst: Bool = false
  ) {
    let clamped = clamp(point, to: screen)
    let path = isPerchPoint(clamped, on: screen)
      ? [clamped]
      : axis(from: feet, to: clamped, verticalFirst: verticalFirst)
    destination = path[0]
    if path.count > 1 { waypoints.insert(path[1], at: 0) }
    walked = 0
    let dx = destination.x - feet.x
    let dy = destination.y - feet.y
    let face = wantsFaceRight(toward: destination, on: screen)
    let horizontal = abs(dx) > abs(dy) + 2
    if face != facingRight {
      pendingFacing = face
      gazeScreen = NSPoint(x: feet.x + (face ? 90 : -90), y: feet.y + 36)
      act = .look(until: Date().timeIntervalSinceReferenceDate + (turning ? 1.1 : 0.55))
      logAct()
      return
    }
    aimYaw(right: face)
    if !horizontal, abs(dy) > 4 {
      gazeScreen = NSPoint(x: feet.x + (face ? 24 : -24), y: feet.y + (dy >= 0 ? 80 : -80))
      act = .look(until: Date().timeIntervalSinceReferenceDate + (turning ? 1.0 : 0.4))
      logAct()
      return
    }
    gazeScreen = nil
    act = .walk
    logAct()
  }

  private func startSide(
    left: Bool, up: Bool, on screen: NSScreen, turning: Bool, bounced: Bool = false
  ) {
    let reach = ChameleonPose.headReach
    let x = left ? screen.visibleFrame.minX + reach : screen.visibleFrame.maxX - reach
    let y = up ? screen.visibleFrame.maxY - 110 : (dockTop(on: screen) ?? screen.visibleFrame.minY) + 16
    if !bounced, edgeLaneBlocked(left: left, on: screen) || inWallGap(NSPoint(x: x, y: y), on: screen) {
      if !columnPerches(on: screen).isEmpty, case .column = branch {
        startSide(left: !left, up: up, on: screen, turning: turning, bounced: true)
        return
      }
      if !columnPerches(on: screen).isEmpty {
        followColumn(up: up, on: screen, turning: turning)
        return
      }
      startSide(left: !left, up: up, on: screen, turning: turning, bounced: true)
      return
    }
    branch = .side(left: left, up: up)
    waypoints = []
    setDestination(NSPoint(x: x, y: y), on: screen, turning: turning)
  }

  private func followDock(right: Bool, on screen: NSScreen, turning: Bool) {
    guard let y = dockTop(on: screen) else {
      startSide(left: false, up: true, on: screen, turning: turning)
      return
    }
    let reach = ChameleonPose.headReach
    let x = right ? screen.visibleFrame.maxX - reach : screen.visibleFrame.minX + reach
    branch = .dock(right: right)
    waypoints = []
    setDestination(NSPoint(x: x, y: y), on: screen, turning: turning, verticalFirst: true)
  }

  private func followColumn(up: Bool, on screen: NSScreen, turning: Bool, reversed: Bool = false) {
    let column = columnPerches(on: screen)
    let next = up
      ? column.filter { perchPoint($0, on: screen).y > feet.y + 12 }.min {
        perchPoint($0, on: screen).y < perchPoint($1, on: screen).y
      }
      : column.filter { perchPoint($0, on: screen).y < feet.y - 12 }.max {
        perchPoint($0, on: screen).y < perchPoint($1, on: screen).y
      }
    if let icon = next {
      let route = routeToPerch(perchPoint(icon, on: screen), icon: icon, on: screen)
      branch = .column(up: up)
      waypoints = Array(route.dropFirst())
      log("approach " + route.map { "\(Int($0.x)),\(Int($0.y))" }.joined(separator: " -> "))
      setDestination(route[0], on: screen, turning: turning)
      return
    }
    if reversed {
      startSide(left: false, up: true, on: screen, turning: true)
      return
    }
    followColumn(up: !up, on: screen, turning: true, reversed: true)
  }

  /// Icons sharing the rightmost column. That column is the branch in the photo.
  private func columnPerches(on screen: NSScreen) -> [NSRect] {
    guard let maxX = icons.map(\.midX).max() else { return [] }
    return icons.filter { abs($0.midX - maxX) < 120 && $0.intersects(screen.visibleFrame.insetBy(dx: -20, dy: -20)) }
      .sorted { $0.maxY < $1.maxY }
  }

  private func nearPerch(on screen: NSScreen) -> Bool {
    columnPerches(on: screen).contains {
      let perch = perchPoint($0, on: screen)
      return hypot(perch.x - feet.x, perch.y - feet.y) < 16
    }
  }

  /// Walk on the open side of the icon, then climb onto the perch. The climb itself is not split,
  /// so the lead foot can reach the top before the body moves.
  private func routeToPerch(_ perch: CGPoint, icon: NSRect, on screen: NSScreen) -> [NSPoint] {
    let solid = solidRect(icon)
    let clearance: CGFloat = 52
    let openX = icon.midX > screen.frame.midX ? solid.minX - clearance : solid.maxX + clearance
    var route: [NSPoint] = []
    if abs(feet.x - openX) > 14 {
      route.append(NSPoint(x: openX, y: feet.y))
    }
    route.append(perch)
    return route
  }

  private func isPerchPoint(_ point: NSPoint, on screen: NSScreen) -> Bool {
    icons.contains {
      let perch = perchPoint($0, on: screen)
      return abs(perch.x - point.x) < 10 && abs(perch.y - point.y) < 10
    }
  }

  /// Feet stay on the icon, far enough from the screen edge that the tail is not in the gap.
  private func perchPoint(_ icon: NSRect, on screen: NSScreen) -> CGPoint {
    let faceLeft = icon.midX > screen.frame.midX
    let tail = ChameleonPose.curledTailReach
    var x = icon.midX
    if faceLeft {
      x = min(x, screen.frame.maxX - tail)
    } else {
      x = max(x, screen.frame.minX + tail)
    }
    x = min(max(x, icon.minX + 4), icon.maxX - 4)
    return CGPoint(x: x, y: icon.maxY)
  }

  private func wantsFaceRight(toward point: CGPoint, on screen: NSScreen) -> Bool {
    if let icon = icons.first(where: {
      abs($0.midX - point.x) < 70 && abs($0.maxY - point.y) < 28
    }) {
      return icon.midX < screen.frame.midX
    }
    if abs(point.x - feet.x) > abs(point.y - feet.y) + 2 {
      return point.x >= feet.x
    }
    return facingRight
  }

  private func aimYaw(right: Bool) {
    let next: CGFloat = right ? 0 : .pi
    if abs(next - yawTarget) > 0.2 {
      log(right ? "turn toward right" : "turn toward left")
    }
    yawTarget = next
    facingRight = right
  }

  private var isClimbing: Bool {
    guard case .walk = act else { return false }
    let dy = destination.y - feet.y
    guard dy > 12, let screen = NSScreen.screens.first else { return false }
    return icons.contains {
      let perch = perchPoint($0, on: screen)
      return abs(perch.x - destination.x) < 10 && abs(perch.y - destination.y) < 10
    }
  }

  private var leadFootIndex: Int { cos(yaw) >= 0 ? 3 : 0 }

  /// The foot that has already gripped the perch stays there while the body comes up.
  private func footIsHoldingPerch(_ index: Int) -> Bool {
    guard isClimbing, index == leadFootIndex, feetSim.indices.contains(index) else { return false }
    let foot = feetSim[index]
    return foot.planted && hypot(foot.world.x - destination.x, foot.world.y - destination.y) < 14
  }

  private func updateYaw(_ dt: CGFloat) {
    var delta = yawTarget - yaw
    if delta > .pi { delta -= 2 * .pi }
    if delta < -.pi { delta += 2 * .pi }
    if abs(delta) < 0.02 {
      yaw = yawTarget
      return
    }
    let step = min(abs(delta), 2.4 * dt)
    yaw += delta > 0 ? step : -step
  }

  /// Icon plus the label under it. The strip between that and the screen edge is a wall
  /// when the chameleon's body cannot fit there.
  private func solidRect(_ icon: NSRect) -> NSRect {
    var rect = icon
    rect.origin.y -= 32
    rect.size.height += 32
    return rect.insetBy(dx: -4, dy: -2)
  }

  /// Curl while sitting, and while the next step is onto a perch, so the tail
  /// can clear the screen edge as the feet move onto the icon.
  private func tailIsCurled(on screen: NSScreen) -> Bool {
    if isStill && nearPerch(on: screen) { return true }
    return isPerchPoint(destination, on: screen)
  }

  private func bodyRect(at anchor: CGPoint, on screen: NSScreen) -> NSRect {
    let forward = cos(yaw)
    let head = anchor.x + forward * ChameleonPose.headReach
    let tailReach = tailIsCurled(on: screen)
      ? ChameleonPose.curledTailReach
      : ChameleonPose.tailReach
    let tail = anchor.x - forward * tailReach
    let minX = min(head, tail)
    let maxX = max(head, tail)
    return NSRect(x: minX, y: anchor.y - 8, width: max(8, maxX - minX), height: 70)
  }

  /// A flush icon leaves no room for the body between the picture and the screen edge.
  private func edgeLaneBlocked(left: Bool, on screen: NSScreen) -> Bool {
    let need = ChameleonPose.headReach + ChameleonPose.curledTailReach
    for icon in icons {
      let solid = solidRect(icon)
      if !left, screen.frame.maxX - solid.maxX < need { return true }
      if left, solid.minX - screen.frame.minX < need { return true }
    }
    return false
  }

  private func inWallGap(_ point: CGPoint, on screen: NSScreen) -> Bool {
    let need = ChameleonPose.headReach + ChameleonPose.curledTailReach
    for icon in icons {
      let solid = solidRect(icon)
      let band = point.y > solid.minY - 24 && point.y < solid.maxY + 36
      if !band { continue }
      if screen.frame.maxX - solid.maxX < need, point.x > solid.maxX - 8 { return true }
      if solid.minX - screen.frame.minX < need, point.x < solid.minX + 8 { return true }
    }
    return false
  }

  /// Torso only. Head and tail may cross an icon; the belly must not sit inside it.
  private func torsoRect(at anchor: CGPoint) -> NSRect {
    let center = anchor.x + cos(yaw) * 18
    return NSRect(x: center - 26, y: anchor.y + 10, width: 52, height: 32)
  }

  private func keepBodyClear(on screen: NSScreen) {
    let before = feet.x
    let rect = bodyRect(at: feet, on: screen)
    if rect.maxX > screen.frame.maxX { feet.x -= rect.maxX - screen.frame.maxX }
    if rect.minX < screen.frame.minX { feet.x += screen.frame.minX - rect.minX }
    let headingForPerch = isPerchPoint(destination, on: screen)
    for icon in icons {
      let solid = solidRect(icon)
      let perched = feet.y >= icon.maxY - 10 && feet.x >= icon.minX - 6 && feet.x <= icon.maxX + 6
      if perched || headingForPerch || !torsoRect(at: feet).intersects(solid) { continue }
      if icon.midX > screen.frame.midX {
        feet.x = min(feet.x, solid.minX - 8)
      } else {
        feet.x = max(feet.x, solid.maxX + 8)
      }
    }
    if abs(feet.x - before) > 2 {
      log("clear \(Int(before)) -> \(Int(feet.x))")
    }
  }

  private func home(_ index: Int) -> CGPoint {
    let offset = ChameleonPose.homes[index]
    return CGPoint(x: feet.x + offset.x * cos(yaw), y: feet.y + offset.y)
  }

  private func plantAllFeet() {
    feetSim = (0..<4).map { index in
      let point = home(index)
      return FootSim(world: point, planted: true, from: point, to: point, swing: 1)
    }
  }

  private func reachFoot(_ index: Int, to target: CGPoint) {
    guard feetSim.indices.contains(index) else { return }
    let sim = feetSim[index]
    if !sim.planted, hypot(sim.to.x - target.x, sim.to.y - target.y) < 6 { return }
    feetSim[index].from = sim.world
    feetSim[index].to = target
    feetSim[index].swing = 0
    feetSim[index].planted = false
  }

  private func updateFeet(_ dt: CGFloat) {
    if feetSim.count != 4 { plantAllFeet() }
    for index in feetSim.indices where !feetSim[index].planted {
      feetSim[index].swing += dt / 0.38
      if feetSim[index].swing >= 1 {
        feetSim[index].swing = 1
        feetSim[index].planted = true
        feetSim[index].world = feetSim[index].to
      } else {
        let t = feetSim[index].swing
        let from = feetSim[index].from
        let to = feetSim[index].to
        feetSim[index].world = CGPoint(
          x: from.x + (to.x - from.x) * t,
          y: from.y + (to.y - from.y) * t + sin(t * .pi) * 10)
      }
    }
    let active = stepPair == 0 ? [0, 3] : [1, 2]
    if pairBusy {
      let stillMoving = active.contains { !feetSim[$0].planted && !footIsHoldingPerch($0) }
      if stillMoving { return }
      pairBusy = false
      stepPair = 1 - stepPair
    }
    guard case .walk = act, abs(yaw - yawTarget) < 0.28 else { return }
    let pair = stepPair == 0 ? [0, 3] : [1, 2]
    let movers = pair.filter { !footIsHoldingPerch($0) }
    if movers.isEmpty || movers.contains(where: { !feetSim[$0].planted }) { return }
    let due = movers.contains { hypot(feetSim[$0].world.x - home($0).x, feetSim[$0].world.y - home($0).y) > 18 }
    if !due { return }
    for index in movers {
      feetSim[index].from = feetSim[index].world
      feetSim[index].to = home(index)
      feetSim[index].swing = 0
      feetSim[index].planted = false
    }
    pairBusy = true
    log("step \(movers.map(String.init).joined(separator: ","))")
  }

  private func eyeTargets() -> (CGPoint, CGPoint) {
    let cursor = NSEvent.mouseLocation
    let lead = gazeScreen ?? CGPoint(x: feet.x + cos(yawTarget) * 90, y: feet.y + 34)
    let time = CGFloat(Date().timeIntervalSinceReferenceDate)
    let scan = CGPoint(x: feet.x + sin(time * 0.7) * 70, y: feet.y + 56 + cos(time * 0.45) * 24)
    let free = hypot(cursor.x - lead.x, cursor.y - lead.y) > 36 ? cursor : scan
    return (lead, free)
  }

  private func noteIcons(on screen: NSScreen) {
    guard !didJoinColumn, !columnPerches(on: screen).isEmpty else { return }
    didJoinColumn = true
    guard case .side = branch else { return }
    followColumn(up: true, on: screen, turning: true)
  }

  /// Top of a bottom Dock. A Dock on the side, or a hidden Dock, has no shelf.
  private func dockTop(on screen: NSScreen) -> CGFloat? {
    let bottomGap = screen.visibleFrame.minY - screen.frame.minY
    let sideDock =
      abs(screen.visibleFrame.minX - screen.frame.minX) > 20
      || abs(screen.frame.maxX - screen.visibleFrame.maxX) > 20
    if sideDock || bottomGap < 20 { return nil }
    return screen.visibleFrame.minY
  }

  private func clamp(_ point: NSPoint, to screen: NSScreen) -> NSPoint {
    let frame = screen.frame.insetBy(dx: 8, dy: 8)
    return NSPoint(
      x: min(max(point.x, frame.minX), frame.maxX),
      y: min(max(point.y, frame.minY), frame.maxY))
  }

  private func place(on screen: NSScreen) {
    guard let petWindow else { return }
    var bounds = NSRect(
      x: feet.x + swayX - PetMetrics.anchor.x,
      y: feet.y + swayY - PetMetrics.anchor.y,
      width: PetMetrics.windowSize.width,
      height: PetMetrics.windowSize.height)
    for sim in feetSim {
      bounds = bounds.union(NSRect(x: sim.world.x - 16, y: sim.world.y - 16, width: 32, height: 32))
    }
    let origin = bounds.origin
    let eyes = eyeTargets()
    var pose = ChameleonPose()
    pose.body = CGPoint(x: feet.x + swayX - origin.x, y: feet.y + swayY - origin.y)
    pose.yaw = yaw
    pose.pitch = pitch
    pose.tailCurl = tailIsCurled(on: screen) ? 0.9 : 0.15
    pose.sway = swayX + swayY
    pose.feet = feetSim.map {
      ChameleonFoot(
        position: CGPoint(x: $0.world.x - origin.x, y: $0.world.y - origin.y),
        planted: $0.planted)
    }
    pose.eyeLeft = CGPoint(x: eyes.0.x - origin.x, y: eyes.0.y - origin.y)
    pose.eyeRight = CGPoint(x: eyes.1.x - origin.x, y: eyes.1.y - origin.y)
    petView.pose = pose
    petWindow.setFrame(bounds, display: true)
  }

  private func refreshIcons() {
    guard !refreshingIcons else { return }
    refreshingIcons = true
    if !askedFinder {
      askedFinder = true
      log("asking Finder for icon positions")
    }
    let script = Self.iconScript
    iconQueue.async { [weak self] in
      var error: NSDictionary?
      let result = NSAppleScript(source: script)?.executeAndReturnError(&error)
      let text = result?.stringValue
      let number = (error?[NSAppleScript.errorNumber] as? NSNumber)?.intValue
      let message = error?[NSAppleScript.errorMessage] as? String
      DispatchQueue.main.async {
        guard let self else { return }
        self.refreshingIcons = false
        guard let screen = NSScreen.screens.first else { return }
        if let number {
          self.iconError = "アイコン位置が取れていない"
          self.log("finder error \(number) \(message ?? "")")
          return
        }
        guard let text else {
          self.iconError = "アイコン位置が取れていない"
          self.log("finder returned no text")
          return
        }
        self.iconError = nil
        self.applyIcons(text, screen: screen)
      }
    }
  }

  /// Finder reports {-1,-1} for icons it has not given a stored position. Those are
  /// skipped. A made-up grid would sit the chameleon on empty wallpaper.
  private func applyIcons(_ text: String, screen: NSScreen) {
    let lines = text.split(whereSeparator: \.isNewline)
    guard let first = lines.first else {
      iconError = "アイコン位置が取れていない"
      log("finder payload unreadable")
      return
    }
    let header = first.split(separator: ",")
    guard let size = Double(header[0]), size >= 16, size <= 512 else {
      iconError = "アイコン位置が取れていない"
      log("finder payload unreadable")
      return
    }
    iconSize = CGFloat(size)
    var rects: [NSRect] = []
    var sample: String?
    var skipped = 0
    for line in lines.dropFirst() {
      let parts = line.split(separator: ",")
      guard parts.count == 2, let fx = Double(parts[0]), let fy = Double(parts[1]) else { continue }
      if fx < 0 || fy < 0 {
        skipped += 1
        continue
      }
      if sample == nil { sample = String(line) }
      let rect = Self.iconRect(fx: fx, fy: fy, size: iconSize, screen: screen)
      if rect.intersects(screen.frame) { rects.append(rect) }
    }
    icons = rects
    skippedIcons = skipped
    if loggedIconCount != rects.count {
      loggedIconCount = rects.count
      log("icons \(rects.count) size \(Int(iconSize)) skipped \(skipped)")
      if let sample, let first = rects.first {
        log("sample finder \(sample) -> \(rectText(first))")
      }
    }
    updateFeetView(on: screen)
    noteIcons(on: screen)
  }

  private func writePreview() {
    let bounds = petView.bounds
    guard bounds.width > 1, bounds.height > 1 else { return }
    guard let rep = NSBitmapImageRep(
      bitmapDataPlanes: nil,
      pixelsWide: Int(bounds.width * 2),
      pixelsHigh: Int(bounds.height * 2),
      bitsPerSample: 8,
      samplesPerPixel: 4,
      hasAlpha: true,
      isPlanar: false,
      colorSpaceName: .deviceRGB,
      bytesPerRow: 0,
      bitsPerPixel: 0)
    else { return }
    rep.size = bounds.size
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
    petView.draw(bounds)
    NSGraphicsContext.restoreGraphicsState()
    guard let data = rep.representation(using: .png, properties: [:]) else { return }
    let url = URL(fileURLWithPath: "/tmp/desktop-pet-preview.png")
    do {
      try data.write(to: url)
      log("wrote preview")
    } catch {
      log("preview failed")
    }
  }

  private func updateFeetView(on screen: NSScreen) {
    let origin = screen.frame.origin
    feetView.icons = icons.map {
      NSRect(x: $0.minX - origin.x, y: $0.minY - origin.y, width: $0.width, height: $0.height)
    }
    if let dock = dockTop(on: screen) {
      feetView.dockY = dock - origin.y
    } else {
      feetView.dockY = nil
    }
    feetView.needsDisplay = true
  }

  private func logAct() {
    let dx = Int(destination.x - feet.x)
    let dy = Int(destination.y - feet.y)
    log("\(modeLabel) leg \(dx),\(dy)")
  }

  private func rectText(_ rect: NSRect) -> String {
    "\(Int(rect.minX)),\(Int(rect.minY)) \(Int(rect.width))x\(Int(rect.height))"
  }

  private func log(_ message: String) {
    NSLog("desktop-pet: \(message)")
    let line = "\(message)\n"
    guard let data = line.data(using: .utf8) else { return }
    if let handle = FileHandle(forWritingAtPath: PetMetrics.logPath) {
      handle.seekToEndOfFile()
      handle.write(data)
      try? handle.close()
    } else {
      FileManager.default.createFile(atPath: PetMetrics.logPath, contents: data)
    }
  }

  private static let iconScript = """
    tell application "Finder"
      set iconSize to 64
      set textSize to 12
      try
        set opt to icon view options of window of desktop
        set iconSize to icon size of opt
        set textSize to text size of opt
      end try
      set rows to {}
      try
        set positions to desktop position of every file of desktop
        repeat with p in positions
          set end of rows to ((item 1 of p) as integer as text) & "," & ((item 2 of p) as integer as text)
        end repeat
      end try
      try
        set positions to desktop position of every folder of desktop
        repeat with p in positions
          set end of rows to ((item 1 of p) as integer as text) & "," & ((item 2 of p) as integer as text)
        end repeat
      end try
      set AppleScript's text item delimiters to linefeed
      return (iconSize as text) & "," & (textSize as text) & linefeed & (rows as text)
    end tell
    """
}

@main
struct DesktopPetMain {
  static func main() {
    let application = NSApplication.shared
    let controller = PetApp()
    application.setActivationPolicy(.accessory)
    application.delegate = controller
    application.run()
  }
}
