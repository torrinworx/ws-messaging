import { h, Button } from "destamatic-ui";
import { Observer } from "destam-dom";

const Home = () => {
    const message = Observer.mutable('');

    const callJob = async () => {
        // Adjust the WebSocket URL according to your backend configuration
        const ws = new WebSocket('ws://localhost:3000/websocket');

        ws.onopen = () => {
            console.log('WebSocket connection opened');
            const jobName = "test"; // Replace with your actual job name
            const params = { test: "value" };  // Replace with your actual parameters
            const jobPayload = new TextEncoder().encode(JSON.stringify(params));
            const nameBuffer = new TextEncoder().encode(jobName.padEnd(8, ' '));
            const combinedPayload = new Uint8Array([...nameBuffer, ...jobPayload]);

            ws.send(combinedPayload);
        };

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.status === 'success') {
                message.set(`Job completed: ${data.result}`);
            } else {
                message.set(`Error: ${data.message}`);
            }
        };

        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            message.set('WebSocket error occurred.');
        };

        ws.onclose = () => {
            console.log('WebSocket connection closed');
        };
    };

    return <div>
        <Button label='Test' onMouseDown={callJob} />
        {message.map(m => m ? m : null)}
    </div>;
};

export default Home;
