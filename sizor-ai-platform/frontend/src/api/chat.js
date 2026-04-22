import client from "./client";

export const getChatModels = (patientId) =>
  client.get(`/patients/${patientId}/chat/models`).then((r) => r.data);

export const sendChatMessage = (patientId, messages, model) =>
  client.post(`/patients/${patientId}/chat`, {
    messages,
    model,
    timezone_offset_minutes: -new Date().getTimezoneOffset(), // e.g. 60 for BST
  }).then((r) => r.data);

export const sendWardChatMessage = (messages, model) =>
  client.post(`/ward/chat`, { messages, model }).then((r) => r.data);
