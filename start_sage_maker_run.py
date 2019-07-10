import boto3
import time
from botocore.vendored import requests
##### you need to install websocket-client, not websocket. This is imperative, or else it won't work!! #####
##### e.g. pip install websocket-client #####
import websocket

# connect to sagemaker using boto3
sm_client = boto3.client('sagemaker')

# notebook we want to activate
notebook_instance = 'wosTest'
notebook_name = 'sage_sw'

# this starts the notebook, it takes some time to do so, so let it sleep for a bit.
sm_client.start_notebook_instance(NotebookInstanceName=notebook_instance)

# self-explanatory - the notebook needs time to start up before you try and get the url in the next step. Five minutes seems to be a good window for this.
print('Going to sleep for 5 minutes to allow the notebook to come online')
time.sleep(300)

# gets an authorized URL to the notebook based on the sagemaker client we use above. This uses aws creds to make sure we can 
# execute commands on the notebook
url = sm_client.create_presigned_notebook_instance_url(NotebookInstanceName=notebook_instance)['AuthorizedUrl']

# some stuff I found in this stack overflow post: https://stackoverflow.com/questions/55781509/automate-the-execution-of-a-ipynb-file-in-sagemaker
url_tokens = url.split('/')
http_proto = url_tokens[0]
http_hn = url_tokens[2].split('?')[0].split('#')[0]

s = requests.Session()
r = s.get(url)
cookies = "; ".join(key + "=" + value for key, value in s.cookies.items())

ws = websocket.create_connection(
    "wss://{}/terminals/websocket/1".format(http_hn),
    cookie=cookies,
    host=http_hn,
    origin=http_proto + "//" + http_hn,
    timeout=1
)

# we send commands one at a time up to the notebook to 1) activate the jupyter env, 2) activate mxnet_p36, then 3) execute
# the .ipynb file. NOTE: we use the \\r as a carriage return character. We need to use this otherwise the commands won't
# run on the remote machine.
ws.send("""["stdin", "source activate root\\r"]""")
time.sleep(3)
print(ws.recv_frame())

# activate mxnet_p36
ws.send("""["stdin", "source activate mxnet_p36\\r"]""")
time.sleep(3)
print(ws.recv_frame())

# run the notebook we want to run
ws.send("""["stdin", "jupyter nbconvert --execute --to notebook --inplace /home/ec2-user/SageMaker/{}.ipynb --ExecutePreprocessor.kernel_name=python3 --ExecutePreprocessor.timeout=1500\\r"]""".format(notebook_name))
time.sleep(3)
print(ws.recv_frame())

status = True

while status:
    
    try:
        
        print(ws.recv_frame())
        time.sleep(2)
        
    except:
        
        print('No more info from stdout')
        status = False
        break
    
time.sleep(30)

print('notebook shutting down...')

# shut down the notebook.
sm_client.stop_notebook_instance(NotebookInstanceName=notebook_instance)

print('notebook shut down complete')

# close the socket connection.
ws.close()
