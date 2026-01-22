"""
Toast notification widget for displaying floating messages to users.
"""
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect
from PyQt6.QtGui import QFont, QPainter, QColor, QPainterPath
from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout, QPushButton, QGraphicsOpacityEffect


class ToastNotification(QWidget):
    """Floating toast notification widget that auto-dismisses."""
    
    # Class variable to track all active toasts for stacking
    _active_toasts = []
    
    # Toast types with their colors
    TYPES = {
        'error': {'bg': '#dc3545', 'icon': '✕'},
        'warning': {'bg': '#fd7e14', 'icon': '⚠'},
        'info': {'bg': '#0d6efd', 'icon': 'ℹ'},
        'success': {'bg': '#198754', 'icon': '✓'},
    }
    
    def __init__(self, parent, message, toast_type='error', duration=5000):
        """
        Create a toast notification.
        
        Args:
            parent: Parent widget (main window)
            message: Message to display
            toast_type: One of 'error', 'warning', 'info', 'success'
            duration: Auto-dismiss duration in milliseconds (0 = no auto-dismiss)
        """
        super().__init__(parent)
        
        self.duration = duration
        self.toast_type = toast_type
        
        # Get type config
        type_config = self.TYPES.get(toast_type, self.TYPES['error'])
        self.bg_color = QColor(type_config['bg'])
        icon = type_config['icon']
        
        # Setup widget as overlay (no special window flags - just a child widget)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setAutoFillBackground(False)
        
        # Create layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)
        
        # Icon label
        icon_label = QLabel(icon)
        icon_label.setFont(QFont('Arial', 14))
        icon_label.setStyleSheet('color: white; background: transparent;')
        layout.addWidget(icon_label)
        
        # Message label
        self.message_label = QLabel(message)
        self.message_label.setFont(QFont('Microsoft YaHei', 10))
        self.message_label.setStyleSheet('color: white; background: transparent;')
        self.message_label.setWordWrap(True)
        self.message_label.setMaximumWidth(350)
        layout.addWidget(self.message_label, 1)
        
        # Close button
        close_btn = QPushButton('×')
        close_btn.setFixedSize(24, 24)
        close_btn.setFont(QFont('Arial', 14, QFont.Weight.Bold))
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet('''
            QPushButton {
                color: white;
                background: transparent;
                border: none;
                border-radius: 12px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.2);
            }
        ''')
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)
        
        # Opacity effect for fade animation
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(0)
        
        # Animations
        self.fade_in_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_in_animation.setDuration(200)
        self.fade_in_animation.setStartValue(0)
        self.fade_in_animation.setEndValue(1.0)
        self.fade_in_animation.setEasingCurve(QEasingCurve.Type.OutQuad)
        
        self.fade_out_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_out_animation.setDuration(300)
        self.fade_out_animation.setStartValue(1.0)
        self.fade_out_animation.setEndValue(0)
        self.fade_out_animation.setEasingCurve(QEasingCurve.Type.InQuad)
        self.fade_out_animation.finished.connect(self._on_fade_out_finished)
        
        # Auto-dismiss timer
        if duration > 0:
            self.dismiss_timer = QTimer(self)
            self.dismiss_timer.setSingleShot(True)
            self.dismiss_timer.timeout.connect(self._start_fade_out)
        else:
            self.dismiss_timer = None
    
    def paintEvent(self, event):
        """Draw rounded rectangle background."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw rounded rectangle
        path = QPainterPath()
        path.addRoundedRect(QRect(0, 0, self.width(), self.height()).toRectF(), 8, 8)
        painter.fillPath(path, self.bg_color)
        
        super().paintEvent(event)
    
    def show_toast(self):
        """Show the toast with fade-in animation."""
        # Add to active toasts
        ToastNotification._active_toasts.append(self)
        
        # Adjust size first
        self.adjustSize()
        
        # Calculate position (top-right corner, stacked)
        self._update_position()
        
        # Show widget - raise it above other widgets
        self.show()
        self.raise_()
        
        # Start fade-in animation
        self.fade_in_animation.start()
        
        # Start auto-dismiss timer
        if self.dismiss_timer:
            self.dismiss_timer.start(self.duration)
    
    def _update_position(self):
        """Update position based on parent and other active toasts."""
        if not self.parent():
            return
        
        parent_rect = self.parent().rect()
        margin = 20
        
        # Calculate vertical offset based on other toasts
        y_offset = margin
        for toast in ToastNotification._active_toasts:
            if toast is self:
                break
            if toast.isVisible():
                y_offset += toast.height() + 10
        
        # Position at top-right
        x = parent_rect.width() - self.width() - margin
        y = y_offset
        
        self.move(x, y)
    
    def _start_fade_out(self):
        """Start the fade-out animation."""
        self.fade_out_animation.start()
    
    def _on_fade_out_finished(self):
        """Handle fade-out completion."""
        self.close()
    
    def close(self):
        """Close the toast and update other toasts' positions."""
        # Remove from active toasts
        if self in ToastNotification._active_toasts:
            ToastNotification._active_toasts.remove(self)
        
        # Update positions of remaining toasts
        for toast in ToastNotification._active_toasts:
            toast._update_position()
        
        super().close()
    
    def mousePressEvent(self, event):
        """Close toast on click."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.close()


def show_toast(parent, message, toast_type='error', duration=5000):
    """
    Convenience function to show a toast notification.
    
    Args:
        parent: Parent widget (main window)
        message: Message to display
        toast_type: One of 'error', 'warning', 'info', 'success'
        duration: Auto-dismiss duration in milliseconds (0 = no auto-dismiss)
    
    Returns:
        ToastNotification: The created toast widget
    """
    toast = ToastNotification(parent, message, toast_type, duration)
    toast.show_toast()
    return toast

