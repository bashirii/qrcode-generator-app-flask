
import grpc
from concurrent import futures
import qr_service_pb2
import qr_service_pb2_grpc
from app import generate_qr_code, get_qr_codes, increment_scan_count, delete_qr_code
from flask import url_for

class QRCodeServicer(qr_service_pb2_grpc.QRCodeServiceServicer):
    def GenerateQRCode(self, request, context):
        qr_id, img_filename = generate_qr_code(request.content)
        return qr_service_pb2.GenerateResponse(
            id=qr_id,
            filename=img_filename,
            url=url_for('static', filename=img_filename, _external=True)
        )

    def ListQRCodes(self, request, context):
        qr_codes = get_qr_codes()
        return qr_service_pb2.ListResponse(
            qr_codes=[
                qr_service_pb2.QRCodeInfo(
                    id=qr[0],
                    content=qr[1],
                    created_at=qr[2],
                    scan_count=qr[3],
                    filename=qr[4],
                    url=url_for('static', filename=qr[4], _external=True)
                ) for qr in qr_codes
            ]
        )

    def GetQRCode(self, request, context):
        qr_codes = get_qr_codes()
        qr = next((qr for qr in qr_codes if qr[0] == request.id), None)
        if qr is None:
            context.abort(grpc.StatusCode.NOT_FOUND, "QR Code not found")
        return qr_service_pb2.QRCodeInfo(
            id=qr[0],
            content=qr[1],
            created_at=qr[2],
            scan_count=qr[3],
            filename=qr[4],
            url=url_for('static', filename=qr[4], _external=True)
        )

    def IncrementScanCount(self, request, context):
        success = increment_scan_count(request.id)
        return qr_service_pb2.IncrementResponse(success=success)

    def DeleteQRCode(self, request, context):
        success = delete_qr_code(request.id)
        return qr_service_pb2.DeleteResponse(success=success)

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    qr_service_pb2_grpc.add_QRCodeServiceServicer_to_server(QRCodeServicer(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print("gRPC server started on port 50051")
    server.wait_for_termination()

if __name__ == '__main__':
    serve()

