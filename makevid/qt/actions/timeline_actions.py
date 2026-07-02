"""timeline_actions — inpaint e manipulação de itens na timeline."""

from pathlib import Path
from PySide6.QtCore import QTimer
from makevid.config import PROJECTS_DIR


class TimelineActionsMixin:

    def _show_inpaint(self):
        import cv2
        clips = sorted(self.project.clips, key=lambda c: c.position)
        t = self.timeline.playhead_pos
        current = 0.0
        for clip in clips:
            if current <= t < current + clip.duration and clip.video_path and Path(clip.video_path).exists():
                cap = cv2.VideoCapture(str(clip.video_path))
                fps = cap.get(cv2.CAP_PROP_FPS) or 16
                cap.set(cv2.CAP_PROP_POS_FRAMES, int((t - current) * fps))
                ret, frame = cap.read()
                cap.release()
                if ret:
                    self.inpaint_panel.set_frame(frame[:, :, ::-1])
                    self._left_stack.setCurrentWidget(self.inpaint_panel)
                    return
            current += clip.duration
        self.generator._status.setText("Nenhum frame no playhead")

    def _do_inpaint(self, params):
        from makevid.services.inpainting_service import InpaintingService
        svc = InpaintingService()
        svc.inpaint_region(
            frame=params["frame"], mask=params["mask"], prompt=params["prompt"],
            project_id=self.project.id,
            on_progress=lambda msg: QTimer.singleShot(0, lambda: self.inpaint_panel._status.setText(msg)),
            on_done=lambda result: QTimer.singleShot(0, lambda: self.inpaint_panel.on_done(result)),
            on_error=lambda err: QTimer.singleShot(0, lambda: self.inpaint_panel.on_error(err)),
        )
