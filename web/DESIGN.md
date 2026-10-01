# CrowdSight Frontend Design Specification & Design Log

## 1. Problem Definition & Target Persona
- **Primary Persona**: Vietnamese field operators and forensic video analysts monitoring recorded CCTV footage from fixed cameras.
- **Context of Use**: Focused analysis sessions spanning multiple consecutive hours in control rooms or investigative desks.
- **Core Mission**: Truthfully correlate visible person counts detected by the model within named image polygons against recorded video footage over time.
- **Essential UX Invariant**: The interface must NEVER misrepresent absence of visual evidence (`UNKNOWN`, `STALE`, `NOT_FULLY_OBSERVED`) as "zero persons". Uncalibrated raw scores must never be portrayed as percentage probabilities or safety thresholds.

---

## 2. Pass 1: Design System Plan

### 2.1 Color Palette
A curated palette adhering to Okabe–Ito colorblind-accessible standards and dark neutral control-room ergonomics:

| Color Name | Hex Code | Role |
| :--- | :--- | :--- |
| **Abyssal Base** | `#0C1017` | Canvas background, deep calm foundation |
| **Console Deck** | `#141B26` | Card surfaces, player workspace background |
| **Subtle Contour** | `#222D3E` | Crisp structural borders and dividers |
| **Signal Gold** | `#E69F00` | Primary interactive accent (Okabe–Ito Amber) |
| **Text Primary** | `#F0F4F8` | High-contrast body, headers, timestamps |
| **Text Muted** | `#8A98A8` | Secondary metadata and unit labels |

#### Zone Identification Colors (Okabe–Ito Accessible, Distinct from Quality States):
- **Zone A**: Okabe Sky Blue (`#56B4E9`)
- **Zone B**: Okabe Bluish Green (`#009E73`)
- **Zone C**: Okabe Vermilion (`#D55E00`)
- **Zone D**: Okabe Purple (`#CC79A7`)

#### Observation Quality States (Triple Encoding: Color + Icon + Pattern + Text):
- **VALID**: Emerald Mint (`#2EC4B6`) + Check Circle `[✓]` + Solid
- **PARTIAL**: Ochre Sand (`#E7A93B`) + Half Circle `[◐]` + Diagonal Hatching
- **UNKNOWN**: Steel Slate (`#7E8B9B`) + Warning Circle `[?]` + Dot Stipple
- **STALE**: Dusty Plum (`#A25B7B`) + Clock `[⌛]` + Crosshatch

### 2.2 Typography
- **Primary Typeface**: `Plus Jakarta Sans` / `Be Vietnam Pro` (Full Vietnamese diacritics coverage, clean humanist geometry).
- **Numeric Font**: Tabular figures via CSS `font-variant-numeric: tabular-nums` for timestamps (`00:04.20s`), frame numbers, and counts to prevent visual jitter.
- **Hierarchy Scale**:
  - `Display / Scrubber Time`: 28px, Bold, Tabular
  - `Header Section`: 18px, Semi-Bold, Sentence case
  - `Body / Zone Cards`: 14px, Regular, 1.5 line height (lines strictly < 80ch)
  - `Footage Metadata / Disclaimers`: 12px, Regular, Tabular

### 2.3 ASCII Wireframe: The "Footage Console" Review Screen
```text
+----------------------------------------------------------------------------------------------------+
| [BANNER] Thử nghiệm — chưa được duyệt cho vận hành thực tế. Cảnh báo vận hành đang tắt. [Mô phỏng] |
+----------------------------------------------------------------------------------------------------+
| CrowdSight  |  Buổi xem: 09/30 Sảnh Đông [SYNTHETIC]        | Model: crowd_best_local_v2 (12824a9) |
+-------------------------------------------------------------+--------------------------------------+
|                                                             | BẢNG VÙNG QUAN SÁT (ZONE STATUS)     |
|                   MÀN HÌNH FOOTAGE CHÍNH                    | +----------------------------------+ |
|             [ <video> + <canvas> đồng bộ ]                  | | [A] Lối vào chính                | |
|                                                             | |     14 người nhìn thấy           | |
|     (Hộp bounding box người + Polygon zone màu sắc)         | |     [VALID] Quan sát đầy đủ      | |
|                                                             | +----------------------------------+ |
|                                                             | | [B] Khu chờ thang máy            | |
|                                                             | |     Chưa quan sát đầy đủ vùng này | |
|                                                             | |     [PARTIAL - Không có số liệu] | |
|                                                             | +----------------------------------+ |
|                                                             |                                      |
|                                                             | KHOẢNH KHẮC NỔI BẬT (HIGHLIGHTS)     |
|                                                             | - 00:04.20: Đạt 14 người tại Lối vào |
|                                                             | - 00:12.80: Đạt 11 người tại Lối vào |
+-------------------------------------------------------------+--------------------------------------+
| [PLAY] [<< 1s] [>> 1s] [1x/2x]  00:04.20 / 01:00.00  [Heatmap: Mờ 60%] [Lớp Zone: BẬT]             |
+----------------------------------------------------------------------------------------------------+
| THANH DÒNG THỜI GIAN ĐA TẦNG (UNIFIED SESSION TIMELINE SCRUBBER)                                   |
| [Trạng thái chất lượng]: [ VALID ][ PARTIAL ][ UNKNOWN ][ VALID ][ STALE ][ VALID ]               |
| [Đường xu hướng Zone A]:  .../---\___/------\.......                                              |
| [Đường xu hướng Zone B]:  .../-------\.......[TRỐNG]......                                         |
| [Ghi chú / Đánh dấu]:           [Note 1]                 [Note 2]                                  |
+----------------------------------------------------------------------------------------------------+
| TAB: Tóm tắt chất lượng (Ratios) | Về phép đo này (Semantics) | Provenance & Hash | Xuất dữ liệu   |
+----------------------------------------------------------------------------------------------------+
```

---

## 3. Pass 2: Critique & Self-Correction (De-AI Dashboard Audit)

### 3.1 Critique Findings
1. **Generic SaaS Card Syndrome**: Typical AI dashboards wrap every single stat into identical rounded rectangle cards with heavy drop shadows and decorative gradients.
   - *Correction*: Discarded generic cards. The footage display is the undisputed hero component (occupying 65% of viewport). Surrounding panels are structured as an integrated cockpit bench with subtle flat divider rules (`#222D3E`) and zero decorative gradients.
2. **Neon Alert & Acid Accents**: Typical AI mockups use vibrant neon lime or radioactive amber for accents that cause severe visual fatigue in dark control rooms.
   - *Correction*: Adopted warm Okabe–Ito amber (`#E69F00`) and deep sea slate. Zone colors follow distinct colorblind-safe frequencies.
3. **Misleading Zero Display**: Default dashboards display `0` when data is missing or empty.
   - *Correction*: Strict visual distinction. An explicit confirmation badge ("0 người được nhìn thấy — vùng đã quan sát đầy đủ") for true zero vs an amber diagonal hatched badge ("Chưa quan sát đầy đủ vùng này") for unobserved zones. Missing buckets in timeline trends render as physical gaps, never lines dipping to zero.
4. **All-Caps Spaced Lettering & Generic Monospace**: AI dashboards love `UPPERCASE TRACKING-WIDEST` for every label and monospace everywhere.
   - *Correction*: Clean natural sentence case in Vietnamese and English. Monospace / tabular numbers are reserved strictly for numeric quantities and media timestamps.
5. **No Decorative Animations**: No distracting entrance slide-ins or pulsating glow borders. Micro-transitions (<150ms) occur strictly in response to user scrubber interactions.

---

## 4. Frontend Architecture & Technology Stack
- **Framework**: React 18 + TypeScript strict (`noUncheckedIndexedAccess`).
- **Build Tool**: Vite.
- **Styling**: Tailwind CSS with semantic CSS variables defined in `index.css`.
- **UI Primitives**: Radix UI (accessible sliders, dialogs, dropdowns, tooltips).
- **Data Fetching & State**: TanStack Query + Zustand (scrubber position, active zones, overlay toggles).
- **API Client**: `openapi-fetch` generated from `contracts/app-v1/openapi.json`.
- **Validation**: Ajv for client-side v1 observation contract verification.
- **Internationalization**: `i18next` with Vietnamese default (`vi`) and English toggle (`en`).
- **Contract Fixtures Route**: `/dev/states` showing all 6 v1 fixtures (`VALID`, `VALID-zero`, `PARTIAL`, `UNKNOWN`, `STALE`, `tracked`).
