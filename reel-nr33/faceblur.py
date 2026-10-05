"""Detecção e rastreamento de rostos para borrar (MediaPipe face detection)."""
import cv2
import numpy as np
import mediapipe as mp

_fd = mp.solutions.face_detection


class FaceBlur:
    def __init__(self, hold=12, conf=0.35, scale=1.9, max_w=0.28, min_hits=2):
        self.full = _fd.FaceDetection(model_selection=1, min_detection_confidence=conf)
        self.short = _fd.FaceDetection(model_selection=0, min_detection_confidence=conf + 0.1)
        self.tracks = []  # dict(cx, cy, w, h, ttl, hits)
        self.hold = hold
        self.scale = scale
        self.max_w = max_w
        self.min_hits = min_hits

    def _detect(self, rgb):
        h, w = rgb.shape[:2]
        boxes = []
        tiles = [(0, 0, w, h), (0, 0, w, int(h * 0.6)), (0, int(h * 0.4), w, h)]
        # grade 2x3 sobreposta para rostos pequenos (multidões, capacetes)
        for gy in range(3):
            for gx in range(2):
                x0 = int(gx * w * 0.45)
                y0 = int(gy * h * 0.3)
                tiles.append((x0, y0, min(w, x0 + int(w * 0.6)), min(h, y0 + int(h * 0.42))))
        for x0, y0, x1, y1 in tiles:
            crop = np.ascontiguousarray(rgb[y0:y1, x0:x1])
            if crop.shape[0] < 600:
                crop = cv2.resize(crop, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
            for det in (self.full, self.short):
                r = det.process(crop)
                for d in r.detections or []:
                    b = d.location_data.relative_bounding_box
                    score = d.score[0]
                    cx = (x0 + (b.xmin + b.width / 2) * (x1 - x0)) / w
                    cy = (y0 + (b.ymin + b.height / 2) * (y1 - y0)) / h
                    bw = b.width * (x1 - x0) / w
                    bh = b.height * (y1 - y0) / h
                    if not (0.012 < bw < self.max_w):
                        continue
                    if bw > 0.16 and score < 0.7:  # rosto grande precisa de mais confiança
                        continue
                    boxes.append([cx, cy, bw, bh, score])
        out = []
        for b in sorted(boxes, key=lambda b: -b[4]):
            if all(abs(b[0] - o[0]) > max(b[2], o[2]) * 0.6 or abs(b[1] - o[1]) > max(b[3], o[3]) * 0.6
                   for o in out):
                out.append(b)
        return out

    def update(self, rgb):
        dets = self._detect(rgb)
        used = set()
        new = []
        for t in self.tracks:
            best, bd = None, 1e9
            for i, d in enumerate(dets):
                if i in used:
                    continue
                dist = abs(d[0] - t["cx"]) + abs(d[1] - t["cy"])
                if dist < max(t["w"], d[2]) * 1.6 and dist < bd:
                    best, bd = i, dist
            if best is not None:
                used.add(best)
                d = dets[best]
                a = 0.6
                new.append(dict(cx=t["cx"] * (1 - a) + d[0] * a, cy=t["cy"] * (1 - a) + d[1] * a,
                                w=max(d[2], t["w"] * 0.92), h=max(d[3], t["h"] * 0.92),
                                ttl=self.hold, hits=t["hits"] + 1))
            elif t["ttl"] > 0 and t["hits"] >= self.min_hits:
                new.append(dict(t, ttl=t["ttl"] - 1))
        for i, d in enumerate(dets):
            if i not in used:
                new.append(dict(cx=d[0], cy=d[1], w=d[2], h=d[3], ttl=self.hold,
                                hits=self.min_hits if d[4] > 0.8 else 1))
        self.tracks = new
        return [(t["cx"], t["cy"], t["w"], t["h"]) for t in new if t["hits"] >= self.min_hits]

    def apply(self, rgb, boxes=None, extra=()):
        if boxes is None:
            boxes = self.update(rgb)
        boxes = list(boxes) + list(extra)
        h, w = rgb.shape[:2]
        out = rgb.copy()
        for cx, cy, bw, bh in boxes:
            s = max(bw * w, bh * h) * self.scale
            x0, y0 = int(cx * w - s / 2), int(cy * h - s * 0.58)
            x1, y1 = int(x0 + s), int(y0 + s * 1.15)
            x0c, y0c, x1c, y1c = max(0, x0), max(0, y0), min(w, x1), min(h, y1)
            if x1c - x0c < 4 or y1c - y0c < 4:
                continue
            roi = out[y0c:y1c, x0c:x1c]
            k = max(3, int(s / 9))
            small = cv2.resize(roi, (max(1, roi.shape[1] // k), max(1, roi.shape[0] // k)),
                               interpolation=cv2.INTER_AREA)
            pix = cv2.resize(small, (roi.shape[1], roi.shape[0]), interpolation=cv2.INTER_LINEAR)
            pix = cv2.GaussianBlur(pix, (0, 0), max(2, s / 12))
            mask = np.zeros(roi.shape[:2], np.float32)
            cv2.ellipse(mask, ((x0 + x1) // 2 - x0c, (y0 + y1) // 2 - y0c),
                        (int(s / 2), int(s * 1.15 / 2)), 0, 0, 360, 1.0, -1)
            mask = cv2.GaussianBlur(mask, (0, 0), max(1.5, s / 20))[..., None]
            out[y0c:y1c, x0c:x1c] = (pix * mask + roi * (1 - mask)).astype(np.uint8)
        return out
