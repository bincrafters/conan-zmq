#include <zmq.h>

int main()
{
    void *context = zmq_ctx_new();
    void *requester = zmq_socket(context, ZMQ_REQ);
    zmq_close(requester);
    zmq_ctx_destroy (context);
}
