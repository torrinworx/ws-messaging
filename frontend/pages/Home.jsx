import { h, Button } from "destamatic-ui";
import { Observer } from "destam-dom";

const callJob = (jobName, params) => {
    return new Promise((resolve, reject) => {
        const ws = new WebSocket('ws://localhost:3000/websocket');
        const results = [];

        ws.onopen = () => {
            console.log('WebSocket connection opened');
            const jobPayload = new TextEncoder().encode(JSON.stringify(params));
            const nameBuffer = new TextEncoder().encode(jobName.padEnd(8, ' '));
            const combinedPayload = new Uint8Array([...nameBuffer, ...jobPayload]);

            ws.send(combinedPayload);
        };

        ws.onmessage = async (event) => {
            try {
                // Convert Blob to text
                const textData = await event.data.text();
                console.log('Received message:', textData); // Log the received data
                const data = JSON.parse(textData);

                if (data.status === 'success') {
                    results.push(data.result);
                } else {
                    reject(new Error(data.message));
                }
            } catch (error) {
                console.error('Error parsing message:', event.data, error);
                reject(new Error('Error parsing server message.'));
            }
        };

        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            reject(error);
        };

        ws.onclose = () => {
            console.log('WebSocket connection closed');
            if (results.length > 0) {
                const finalResult = `Job completed with results: ${results.join(', ')}`;
                resolve(finalResult);
            } else {
                resolve();
            }
        };
    });
};

const Home = () => {
    const message = Observer.mutable('');

    return <div>
        <Button label='Job 1' onMouseDown={() => callJob('test', { test: 'value1', job_num: '1'})
            .then(result => message.set(result))
        } />
        <Button label='Job 2' onMouseDown={() => callJob('test', { test: 'value2', job_num: '2' })
            .then(result => message.set(result))
        } />
        <Button label='Job 3' onMouseDown={() => callJob('test', { test: 'value3', job_num: '3' })
            .then(result => message.set(result))
            .catch(error => console.error(error))
        } />
        {message.map(m => m ? m : null)}
    </div>;
};

export default Home;
