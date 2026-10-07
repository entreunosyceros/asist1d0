"""
Hoja de estilos global de la interfaz Asist{1d0}.

Tema claro moderno (Fusion + QSS): tipografía, botones, tablas, formularios,
login sin marco, menú superior y bandeja visual coherente.
"""

STYLESHEET = """
/* ── Base ───────────────────────────────────────── */
* {
    outline: none;
}
QWidget {
    font-family: "Inter", "Segoe UI", "Ubuntu", "Noto Sans", sans-serif;
    font-size: 13px;
    color: #0f172a;
}
QMainWindow {
    background: #f4f6fb;
}
QDialog {
    background: #f4f6fb;
    color: #0f172a;
}
QToolTip {
    background: #0f172a;
    color: #f8fafc;
    border: none;
    padding: 6px 10px;
    border-radius: 6px;
}

/* ── Sidebar ────────────────────────────────────── */
#Sidebar {
    background: #111827;
    min-width: 220px;
    max-width: 240px;
}
#SidebarTitle {
    color: #ffffff;
    font-size: 18px;
    font-weight: 700;
    letter-spacing: 0.3px;
    padding: 24px 20px 6px 20px;
}
#SidebarUser {
    color: #9ca3af;
    font-size: 11px;
    padding: 0 20px 20px 20px;
    line-height: 1.4;
}
#Sidebar QPushButton {
    background: transparent;
    color: #d1d5db;
    border: none;
    text-align: left;
    padding: 11px 16px;
    border-radius: 10px;
    margin: 3px 12px;
    font-weight: 500;
}
#Sidebar QPushButton:hover {
    background: #1f2937;
    color: #ffffff;
}
#Sidebar QPushButton:checked {
    background: #2563eb;
    color: #ffffff;
    font-weight: 600;
}
#Sidebar QPushButton#SecondaryButton {
    background: #1f2937;
    color: #e5e7eb;
    margin-top: 8px;
    text-align: center;
}
#Sidebar QPushButton#SecondaryButton:hover {
    background: #374151;
    color: #ffffff;
}

/* ── Contenido ──────────────────────────────────── */
#ContentArea {
    background: #f4f6fb;
}
QLabel#PageTitle {
    font-size: 24px;
    font-weight: 700;
    color: #111827;
    letter-spacing: -0.3px;
}
QLabel#PageSubtitle {
    color: #6b7280;
    font-size: 13px;
}
QLabel#StatusToast {
    background: #ecfdf5;
    color: #065f46;
    border: 1px solid #6ee7b7;
    border-radius: 10px;
    padding: 12px 14px;
    font-size: 14px;
    font-weight: 700;
}
QLabel#StatusToast[error="true"] {
    background: #fef2f2;
    color: #991b1b;
    border: 1px solid #fecaca;
}
QFrame#ActionBanner {
    background: #059669;
    border: 2px solid #047857;
    border-radius: 14px;
    color: #ffffff;
}
QFrame#ActionBanner[error="true"] {
    background: #dc2626;
    border: 2px solid #b91c1c;
}
QLabel#ActionBannerIcon {
    color: #ffffff;
    font-size: 20px;
    font-weight: 800;
    padding-right: 6px;
}
QLabel#ActionBannerText {
    color: #ffffff;
    font-size: 15px;
    font-weight: 700;
}
QLabel#DetailHeading {
    font-size: 18px;
    font-weight: 700;
    color: #111827;
}
QLabel#MetaLabel {
    color: #6b7280;
    font-size: 11px;
    font-weight: 600;
}
QLabel#MetaValue {
    color: #111827;
    font-size: 13px;
}
QWidget#EmptyState {
    background: #ffffff;
    border: 1px dashed #d1d5db;
    border-radius: 14px;
    min-height: 160px;
}
QLabel#EmptyStateMessage {
    color: #6b7280;
    font-size: 14px;
    padding: 12px;
}
QWidget#DetailPanel {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 14px;
}
QListWidget#DetailList {
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    background: #f8fafc;
}
QFrame#TimelinePanel {
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    background: #f8fafc;
}
QLabel#TimelineDay {
    color: #6b7280;
    font-size: 11px;
    font-weight: 700;
    padding: 8px 0 4px 30px;
    letter-spacing: 0.02em;
}
QLabel#TimelineTime {
    color: #6b7280;
    font-size: 12px;
    font-weight: 600;
    font-family: "JetBrains Mono", "Cascadia Mono", "Consolas", monospace;
    padding-top: 4px;
}
QLabel#TimelineTitle {
    color: #111827;
    font-size: 13px;
    font-weight: 600;
}
QLabel#TimelineBody {
    color: #4b5563;
    font-size: 13px;
    font-style: italic;
    padding-left: 2px;
}
QLabel#TimelineEmpty {
    color: #9ca3af;
    font-size: 13px;
    padding: 24px;
}
QFrame#SidebarLogoWrap {
    background: transparent;
    padding: 8px 16px 0 16px;
}
QLabel#KpiValue {
    font-size: 30px;
    font-weight: 700;
    color: #111827;
}
QLabel#KpiLabel {
    color: #6b7280;
    font-size: 12px;
    font-weight: 500;
}
QFrame#KpiCard {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 16px;
    padding: 12px;
}
QFrame#KpiCard:hover {
    border: 1px solid #c7d2fe;
}
QFrame#MetricsPanel {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 16px;
}
QLabel#MetricsPanelTitle {
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 1.2px;
    color: #6b7280;
}
QFrame#MetricsDivider {
    background: #e5e7eb;
    max-height: 1px;
    margin: 4px 0 6px 0;
}
QLabel#MetricLabel {
    color: #4b5563;
    font-size: 13px;
}
QLabel#MetricValue {
    color: #111827;
    font-size: 16px;
    font-weight: 700;
}
QLabel#MetricValue[warn="true"] {
    color: #b91c1c;
}
QFrame#ChartCard {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 16px;
    min-height: 220px;
}
QLabel#ChartTitle {
    font-size: 13px;
    font-weight: 600;
    color: #374151;
}

/* ── Búsqueda global ─────────────────────────────── */
QFrame#GlobalSearchChrome {
    background: #f4f6fb;
    border-bottom: 1px solid #e5e7eb;
}
QLineEdit#GlobalSearchInput {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 10px 14px;
    font-size: 14px;
    min-height: 20px;
}
QLineEdit#GlobalSearchInput:focus {
    border: 1px solid #2563eb;
    background: #ffffff;
}
QFrame#SearchResultsPanel {
    background: #ffffff;
    border: 1px solid #d1d5db;
    border-radius: 12px;
}
QLabel#SearchSectionTitle {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.8px;
    color: #6b7280;
    padding: 8px 10px 2px 10px;
}
QLabel#SearchHint {
    color: #9ca3af;
    padding: 16px 12px;
}
QFrame#SearchHitRow {
    background: transparent;
    border-radius: 8px;
}
QFrame#SearchHitRow[selected="true"] {
    background: #eff6ff;
}
QFrame#SearchHitRow:hover {
    background: #f3f4f6;
}
QLabel#SearchHitTitle {
    font-size: 13px;
    font-weight: 600;
    color: #111827;
}
QLabel#SearchHitSub {
    font-size: 11px;
    color: #6b7280;
}

/* ── Login ──────────────────────────────────────── */
#LoginDialog {
    background: transparent;
    border: none;
}
#LoginCard {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 20px;
}
#LoginCard QLabel {
    color: #111827;
}
#LoginCard QLabel#PageTitle {
    color: #111827;
}
QPushButton#LoginCloseButton {
    background: transparent;
    color: #94a3b8;
    border: none;
    border-radius: 14px;
    padding: 0;
    font-size: 14px;
    font-weight: 600;
    min-height: 0;
}
QPushButton#LoginCloseButton:hover {
    background: #f1f5f9;
    color: #0f172a;
}
QPushButton#LoginCloseButton:pressed {
    background: #e2e8f0;
}

/* ── Botones ────────────────────────────────────── */
QPushButton {
    background: #2563eb;
    color: #ffffff;
    border: none;
    border-radius: 10px;
    padding: 9px 16px;
    font-weight: 600;
    min-height: 18px;
}
QPushButton:hover {
    background: #1d4ed8;
}
QPushButton:pressed {
    background: #1e40af;
}
QPushButton:disabled {
    background: #cbd5e1;
    color: #64748b;
}
QPushButton#SecondaryButton {
    background: #eef2ff;
    color: #1e3a8a;
}
QPushButton#SecondaryButton:hover {
    background: #e0e7ff;
    color: #1e3a8a;
}
QPushButton#DangerButton {
    background: #dc2626;
    color: #ffffff;
}
QPushButton#DangerButton:hover {
    background: #b91c1c;
}

/* ── Campos de formulario (fondo claro → texto oscuro) ── */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QDateEdit {
    background: #ffffff;
    color: #0f172a;
    border: 1px solid #d1d5db;
    border-radius: 10px;
    padding: 8px 12px;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid #2563eb;
    background: #ffffff;
    color: #0f172a;
}
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled {
    background: #f3f4f6;
    color: #9ca3af;
}

/* ── ComboBox / desplegables ────────────────────── */
QComboBox {
    background: #ffffff;
    color: #0f172a;
    border: 1px solid #d1d5db;
    border-radius: 10px;
    padding: 8px 12px;
    padding-right: 28px;
    min-height: 18px;
    combobox-popup: 0;
}
QComboBox:on {
    background: #ffffff;
    color: #0f172a;
    border: 1px solid #2563eb;
}
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 28px;
    border: none;
    background: transparent;
}
QComboBox::down-arrow {
    width: 0;
    height: 0;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #6b7280;
    margin-right: 10px;
}
QComboBox QAbstractItemView {
    background: #ffffff;
    color: #0f172a;
    border: 1px solid #d1d5db;
    border-radius: 10px;
    padding: 4px;
    outline: none;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
}
QComboBox QAbstractItemView::item {
    background: #ffffff;
    color: #0f172a;
    min-height: 28px;
    padding: 6px 10px;
    border-radius: 6px;
}
QComboBox QAbstractItemView::item:hover {
    background: #eff6ff;
    color: #1e3a8a;
}
QComboBox QAbstractItemView::item:selected {
    background: #2563eb;
    color: #ffffff;
}

/* ── Tablas / listas / árboles ──────────────────── */
QTableWidget, QTreeWidget, QListWidget {
    background: #ffffff;
    color: #0f172a;
    border: 1px solid #e5e7eb;
    border-radius: 14px;
    gridline-color: #f1f5f9;
    alternate-background-color: #f8fafc;
    selection-background-color: #dbeafe;
    selection-color: #1e3a8a;
    outline: none;
}
QTableWidget::item, QTreeWidget::item, QListWidget::item {
    color: #0f172a;
    padding: 6px;
}
QTableWidget::item:selected, QTreeWidget::item:selected, QListWidget::item:selected {
    background: #dbeafe;
    color: #1e3a8a;
}
QHeaderView::section {
    background: #f8fafc;
    color: #374151;
    padding: 10px 8px;
    border: none;
    border-bottom: 1px solid #e5e7eb;
    border-right: 1px solid #f1f5f9;
    font-weight: 600;
    font-size: 12px;
}
QHeaderView::section:last {
    border-right: none;
}

/* ── Pestañas ───────────────────────────────────── */
QTabWidget::pane {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 14px;
    top: -1px;
    padding: 8px;
}
QTabBar::tab {
    background: transparent;
    color: #6b7280;
    padding: 10px 16px;
    margin-right: 4px;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
    font-weight: 600;
}
QTabBar::tab:selected {
    background: #ffffff;
    color: #2563eb;
    border: 1px solid #e5e7eb;
    border-bottom: 1px solid #ffffff;
}
QTabBar::tab:hover:!selected {
    color: #111827;
    background: #f3f4f6;
}

/* ── GroupBox / Splitter / Scroll ───────────────── */
QGroupBox {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 14px;
    margin-top: 14px;
    padding: 18px 14px 14px 14px;
    font-weight: 600;
    color: #111827;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 8px;
    color: #374151;
}
QSplitter::handle {
    background: #e5e7eb;
    width: 2px;
    margin: 8px 4px;
    border-radius: 1px;
}
QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 4px 2px;
}
QScrollBar::handle:vertical {
    background: #cbd5e1;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #94a3b8;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
    height: 0;
}
QScrollBar:horizontal {
    background: transparent;
    height: 10px;
    margin: 2px 4px;
}
QScrollBar::handle:horizontal {
    background: #cbd5e1;
    border-radius: 5px;
    min-width: 30px;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: none;
    width: 0;
}

QCheckBox {
    color: #374151;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #d1d5db;
    border-radius: 4px;
    background: #ffffff;
}
QCheckBox::indicator:checked {
    background: #2563eb;
    border: 1px solid #2563eb;
}
#LoginCard QCheckBox {
    color: #374151;
}

QMenuBar {
    background: #ffffff;
    color: #111827;
    border-bottom: 1px solid #e5e7eb;
    padding: 2px 6px;
}
QMenuBar::item {
    background: transparent;
    color: #111827;
    padding: 6px 12px;
    border-radius: 6px;
}
QMenuBar::item:selected {
    background: #eff6ff;
    color: #1e3a8a;
}
QMenuBar::item:pressed {
    background: #dbeafe;
}
QMessageBox QLabel {
    color: #0f172a;
}
QMenu {
    background: #ffffff;
    color: #0f172a;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    padding: 6px;
}
QMenu::item {
    background: transparent;
    color: #0f172a;
    padding: 8px 18px;
    border-radius: 6px;
}
QMenu::item:selected {
    background: #2563eb;
    color: #ffffff;
}
QPlainTextEdit {
    background: #ffffff;
    color: #0f172a;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 10px;
    font-family: "JetBrains Mono", "Cascadia Code", "Consolas", "Ubuntu Mono", monospace;
    font-size: 12px;
}
"""
