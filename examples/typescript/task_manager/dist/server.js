/**
 * Express server for the Task Manager agent.
 *
 * Demonstrates ADK + Express integration with standard and SSE endpoints.
 */
import express from 'express';
import cors from 'cors';
import { InMemoryRunner, isFinalResponse, stringifyContent, } from '@google/adk';
import { createUserContent } from '@google/genai';
import { rootAgent } from './agent.js';
const app = express();
app.use(express.json());
app.use(cors({ origin: 'http://localhost:3000' }));
const runner = new InMemoryRunner({ agent: rootAgent });
async function getOrCreateSession(userId, sessionId) {
    const existing = await runner.sessionService.getSession({
        appName: runner.appName,
        userId,
        sessionId,
    });
    if (existing)
        return existing;
    return runner.sessionService.createSession({
        appName: runner.appName,
        userId,
    });
}
app.post('/chat', async (req, res) => {
    const { message, sessionId, userId = 'default' } = req.body;
    const session = await getOrCreateSession(userId, sessionId);
    const events = [];
    for await (const event of runner.runAsync({
        userId,
        sessionId: session.id,
        newMessage: createUserContent(message),
    })) {
        if (isFinalResponse(event)) {
            events.push({
                type: 'response',
                content: stringifyContent(event),
            });
        }
    }
    res.json({ events });
});
app.get('/chat/stream', async (req, res) => {
    const { message, sessionId, userId = 'default' } = req.query;
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');
    const session = await getOrCreateSession(userId, sessionId);
    for await (const event of runner.runAsync({
        userId,
        sessionId: session.id,
        newMessage: createUserContent(message),
    })) {
        if (event?.content?.parts?.length) {
            res.write(`data: ${JSON.stringify(event)}\n\n`);
        }
    }
    res.write('data: [DONE]\n\n');
    res.end();
});
app.get('/health', (_req, res) => res.json({ status: 'healthy' }));
const PORT = process.env.PORT || 8080;
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
//# sourceMappingURL=server.js.map