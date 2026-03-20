import client from "./client";

export const getChatModels = (patientId) =>
  client.get(`/patients/${patientId}/chat/models`).then((r) => r.data);

export const sendChatMessage = (patientId, messages, model) =>
  client.post(`/patients/${patientId}/chat`, { messages, model }).then((r) => r.data);
