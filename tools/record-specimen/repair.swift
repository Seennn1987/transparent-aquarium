// Fills the black dropouts the specimen scene draws on odd single frames.
//   swift repair.swift <frames-dir>
// A frame with a patch of near-black pixels (the room is pale everywhere) gets those pixels,
// grown by a small margin, replaced by the mean of the nearest clean frames before and after.
// Originals are kept in <frames-dir>/glitched/.
import CoreGraphics
import Foundation
import ImageIO
import UniformTypeIdentifiers

let dir = URL(fileURLWithPath: CommandLine.arguments[1])
let names = try FileManager.default.contentsOfDirectory(atPath: dir.path).filter { $0.hasSuffix(".png") }.sorted()
let space = CGColorSpace(name: CGColorSpace.sRGB)!

struct Frame { var pixels: [UInt8]; let width: Int; let height: Int }

func load(_ name: String) -> Frame {
  let source = CGImageSourceCreateWithURL(dir.appendingPathComponent(name) as CFURL, nil)!
  let image = CGImageSourceCreateImageAtIndex(source, 0, nil)!
  var pixels = [UInt8](repeating: 0, count: image.width * image.height * 4)
  let context = CGContext(data: &pixels, width: image.width, height: image.height, bitsPerComponent: 8,
                          bytesPerRow: image.width * 4, space: space,
                          bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
  context.draw(image, in: CGRect(x: 0, y: 0, width: image.width, height: image.height))
  return Frame(pixels: pixels, width: image.width, height: image.height)
}

func save(_ frame: Frame, _ url: URL) {
  var pixels = frame.pixels
  let context = CGContext(data: &pixels, width: frame.width, height: frame.height, bitsPerComponent: 8,
                          bytesPerRow: frame.width * 4, space: space,
                          bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
  let destination = CGImageDestinationCreateWithURL(url as CFURL, UTType.png.identifier as CFString, 1, nil)!
  CGImageDestinationAddImage(destination, context.makeImage()!, nil)
  CGImageDestinationFinalize(destination)
}

let darkSum = 60
let margin = 4
func dark(_ f: Frame, _ i: Int) -> Bool { Int(f.pixels[i]) + Int(f.pixels[i + 1]) + Int(f.pixels[i + 2]) < darkSum }

func darkCount(_ f: Frame) -> Int {
  var count = 0
  for y in stride(from: 0, to: f.height, by: 2) {
    for x in stride(from: 0, to: f.width, by: 2) where dark(f, (y * f.width + x) * 4) { count += 1 }
  }
  return count
}

let glitched = Set(names.indices.filter { darkCount(load(names[$0])) > 20 })
print("glitched frames:", glitched.sorted())
if glitched.isEmpty { exit(0) }

let keep = dir.appendingPathComponent("glitched")
try FileManager.default.createDirectory(at: keep, withIntermediateDirectories: true)

func nearestClean(_ from: Int, _ step: Int) -> Int? {
  var i = from + step
  while i >= 0 && i < names.count {
    if !glitched.contains(i) { return i }
    i += step
  }
  return nil
}

for index in glitched.sorted() {
  var frame = load(names[index])
  let sources = [nearestClean(index, -1), nearestClean(index, 1)].compactMap { $0 }.map { load(names[$0]) }
  let w = frame.width, h = frame.height
  var mask = [Bool](repeating: false, count: w * h)
  for y in 0..<h {
    for x in 0..<w where dark(frame, (y * w + x) * 4) {
      for yy in max(0, y - margin)...min(h - 1, y + margin) {
        for xx in max(0, x - margin)...min(w - 1, x + margin) { mask[yy * w + xx] = true }
      }
    }
  }
  var filled = 0
  for p in 0..<(w * h) where mask[p] {
    for c in 0..<3 {
      frame.pixels[p * 4 + c] = UInt8(sources.reduce(0) { $0 + Int($1.pixels[p * 4 + c]) } / sources.count)
    }
    filled += 1
  }
  try? FileManager.default.removeItem(at: keep.appendingPathComponent(names[index]))
  try FileManager.default.moveItem(at: dir.appendingPathComponent(names[index]), to: keep.appendingPathComponent(names[index]))
  save(frame, dir.appendingPathComponent(names[index]))
  print("\(names[index]): filled \(filled) px from \(sources.count) neighbours")
}
