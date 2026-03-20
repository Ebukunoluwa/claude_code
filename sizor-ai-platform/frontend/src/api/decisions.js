import client from "./client";

export const createDecision = (callId, data) =>
  client.post(`/calls/${callId}/decision`, data).then((r) => r.data);
export const getDecision = (callId) =>
  client.get(`/calls/${callId}/decision`).then((r) => r.data);
export const respondToDecision = (decisionId, data) =>
  client.post(`/decisions/${decisionId}/respond`, data).then((r) => r.data);
export const getDashboard = () => client.get("/dashboard").then((r) => r.data);
export const getScheduleToday = () => client.get("/schedule/today").then((r) => r.data);
