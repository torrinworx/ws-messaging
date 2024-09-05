import { h, Button } from "destamatic-ui";
import { Observer } from "destam-dom";

let ws;

const callJob = (jobName, params) => {
    return new Promise((resolve, reject) => {
        if (ws && ws.readyState === WebSocket.OPEN) {
            const jobPayload = new TextEncoder().encode(JSON.stringify(params));
            const nameBuffer = new TextEncoder().encode(jobName.padEnd(8, ' '));
            const combinedPayload = new Uint8Array([...nameBuffer, ...jobPayload]);

            ws.send(combinedPayload);

            const onMessage = async (event) => {
                try {
                    const textData = await event.data.text();
                    // TODO: somehow stream the data back through the promise?
                    // idk
                    const data = JSON.parse(textData);

                    if (data.status === 'success') {
                        resolve(data.result);
                    } else {
                        reject(new Error(data.message));
                    }
                } catch (error) {
                    console.error('Error parsing message:', event.data, error);
                    reject(new Error('Error parsing server message.'));
                }
                ws.removeEventListener('message', onMessage);
            };

            const onError = (error) => {
                console.error('WebSocket error:', error);
                reject(error);
                ws.removeEventListener('error', onError);
            };

            ws.addEventListener('message', onMessage);
            ws.addEventListener('error', onError);

        } else {
            reject(new Error('WebSocket connection is not open.'));
        }
    });
};


const Home = ({ Shared }) => {
    const message = Observer.mutable('');

    const initWebSocket = () => {
        ws = new WebSocket('ws://localhost:3000/websocket');
        ws.onopen = () => {
            console.log('WebSocket connection opened');
        };
        ws.onclose = () => {
            console.log('WebSocket connection closed');
        };

        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    };

    initWebSocket();

    return <div>
        Hi there
        <Button label='Job 1' onMouseDown={() => 
            callJob('test', { test: 'value1', job_num: '1'})
                .then(result => message.set(result))
                .catch(error => console.error(error))
        } />
        <Button label='Job 2' onMouseDown={() => 
            callJob('test', { test: 'value2', job_num: '2' })
                .then(result => message.set(result))
                .catch(error => console.error(error))
        } />
        <Button label='Job 3' onMouseDown={() => 
            callJob('test', { test: 'value3', job_num: '3' })
                .then(result => message.set(result))
                .catch(error => console.error(error))
        } />
        <Button label='Hello World' onMouseDown={() => 
            callJob('HelloW', {})
                .then(result => message.set(result))
                .catch(error => console.error(error))
        } />
        {message.map(m => m ? m : null)}
    </div>;
};

export default Home;
