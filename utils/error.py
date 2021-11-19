class RTSPError(Exception):
    """Raised if frame from stream is missing"""
    def __init__(self, frame_status, stream_status):
        self.frame_status = frame_status
        self.stream_status = stream_status

    def __str__(self):
        if not self.stream_status:
            return "Stream closed"
        if not self.frame_status:
            return "Empty frame from stream"
