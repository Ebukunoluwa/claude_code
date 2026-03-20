import client from "./client";

export const getCall = (id) => client.get(`/calls/${id}`).then((r) => r.data);
export const reviewCall = (id) => client.post(`/calls/${id}/review`).then((r) => r.data);
export const raiseFlag = (id, data) => client.post(`/calls/${id}/flag`, data).then((r) => r.data);
export const processCall = (id) => client.post(`/calls/${id}/process`).then((r) => r.data);
