import client from "./client";

export const getPatient = (id) => client.get(`/patients/${id}`).then((r) => r.data);
export const listPatients = () => client.get("/patients").then((r) => r.data);
export const updatePatient = (id, data) => client.put(`/patients/${id}`, data).then((r) => r.data);
export const getPatientCalls = (id) => client.get(`/patients/${id}/calls`).then((r) => r.data);
export const getPatientTrends = (id) => client.get(`/patients/${id}/trends`).then((r) => r.data);
export const getPatientDecisions = (id) => client.get(`/patients/${id}/decisions`).then((r) => r.data);
export const getPatientSchedule = (id) => client.get(`/patients/${id}/schedule`).then((r) => r.data);
export const updateProfile = (id, data) => client.put(`/patients/${id}/profile`, data).then((r) => r.data);

export const actionReview = (id, data) =>
  client.post(`/patients/${id}/actions/review`, data).then((r) => r.data);
export const actionNote = (id, data) =>
  client.post(`/patients/${id}/actions/note`, data).then((r) => r.data);
export const actionProbe = (id, data) =>
  client.post(`/patients/${id}/actions/probe`, data).then((r) => r.data);
export const actionEscalate = (id, data) =>
  client.post(`/patients/${id}/actions/escalate`, data).then((r) => r.data);
export const resolveFlag = (patientId, flagId, data) =>
  client.post(`/patients/${patientId}/actions/resolve-flag/${flagId}`, data).then((r) => r.data);
