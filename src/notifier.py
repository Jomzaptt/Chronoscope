"""Windows Toast 通知"""

import html
import logging
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
from enum import Enum

log = logging.getLogger(__name__)

# Windows 创建标志：防止控制台窗口出现
_CREATE_NO_WINDOW = 0x08000000

# 通知线程池，限制并发
_notification_executor = ThreadPoolExecutor(
    max_workers=2, thread_name_prefix="notif"
)


class NotificationType(Enum):
    INFO = "info"
    WARNING = "warning"
    SUCCESS = "success"
    DAILY_LIMIT = "daily_limit"
    HOURLY_STATS = "hourly_stats"


def _escape_xml(text: str) -> str:
    """转义 XML 特殊字符，防止注入攻击"""
    return html.escape(text, quote=True)


def _notify_win10(title: str, message: str, notif_type: NotificationType = NotificationType.INFO):
    """使用 Windows 10+ 内置通知"""
    try:
        # 根据通知类型添加不同的音频和视觉提示
        audio_attr = ""
        if notif_type == NotificationType.WARNING:
            audio_attr = 'audio src="ms-winsoundevent:Notification.Looping.Alarm" loop="false"'
        elif notif_type == NotificationType.SUCCESS:
            audio_attr = 'audio src="ms-winsoundevent:Notification.Default" loop="false"'
        elif notif_type == NotificationType.DAILY_LIMIT:
            audio_attr = 'audio src="ms-winsoundevent:Notification.Looping.Alarm" loop="false"'
        elif notif_type == NotificationType.HOURLY_STATS:
            audio_attr = 'audio src="ms-winsoundevent:Notification.Default" loop="false"'

        # 转义 XML 特殊字符，防止注入
        safe_title = _escape_xml(title)
        safe_message = _escape_xml(message)

        ps_script = f"""
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom, ContentType = WindowsRuntime] | Out-Null

$template = @"
<toast duration="short">
    <visual>
        <binding template="ToastGeneric">
            <text>{safe_title}</text>
            <text>{safe_message}</text>
        </binding>
    </visual>
    {audio_attr}
</toast>
"@

$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml($template)
$toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
$notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Chronoscope")
$notifier.Show($toast)
"""
        subprocess.Popen(
            ["powershell", "-WindowStyle", "Hidden", "-Command", ps_script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=_CREATE_NO_WINDOW,
        )
    except Exception as e:
        log.debug("Toast notification failed: %s", e)
        _notify_fallback(title, message)


def _notify_fallback(title: str, message: str):
    """备用通知：使用 win32gui 气泡提示"""
    try:
        import win32gui
        import win32con

        # 简单的消息框备用方案
        threading.Thread(
            target=lambda: win32gui.MessageBox(
                0, message, title, win32con.MB_ICONINFORMATION | win32con.MB_SYSTEMMODAL
            ),
            daemon=True,
        ).start()
    except Exception as e:
        log.warning("Fallback notification also failed: %s", e)


def send_notification(
    title: str,
    message: str,
    notif_type: NotificationType = NotificationType.INFO,
):
    """发送 Windows 通知（非阻塞）

    Args:
        title: 通知标题
        message: 通知内容
        notif_type: 通知类型，影响声音和显示样式
    """
    _notification_executor.submit(_notify_win10, title, message, notif_type)
