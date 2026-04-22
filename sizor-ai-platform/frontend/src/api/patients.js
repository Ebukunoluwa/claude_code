import client from "./client";

export const createPatient = (data) => client.post("/patients", data).then((r) => r.data);
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
export const getPatientNotes = (id) =>
  client.get(`/patients/${id}/notes`).then((r) => r.data);

export const actionNote = (id, data) =>
  client.post(`/patients/${id}/actions/note`, data).then((r) => r.data);
export const actionProbe = (id, data) =>
  client.post(`/patients/${id}/actions/probe`, data).then((r) => r.data);
export const actionEscalate = (id, data) =>
  client.post(`/patients/${id}/actions/escalate`, data).then((r) => r.data);

export const getCliniciansList = () =>
  client.get("/patients/clinicians-list").then((r) => r.data);

export const getWards = () =>
  client.get("/patients/wards").then((r) => r.data);

export const getEscalationsInbox = () =>
  client.get("/patients/escalations/inbox").then((r) => r.data);
export const resolveFlag = (patientId, flagId, data) =>
  client.post(`/patients/${patientId}/actions/resolve-flag/${flagId}`, data).then((r) => r.data);

export const getCallPrompt = (id) => client.get(`/patients/${id}/call-prompt`).then((r) => r.data);

export const getPatientPathwayInfo = (id) =>
  client.get(`/patients/${id}/pathway-info`).then((r) => r.data);

export const getPatientPathwayDetails = (id) =>
  client.get(`/patients/${id}/pathway-details`).then((r) => r.data);

export const updatePathway = (id, data) =>
  client.patch(`/patients/${id}/pathway`, data).then((r) => r.data);

export const downloadPatientReport = (id) =>
  client.get(`/patients/${id}/report/pdf`, { responseType: "blob" }).then((r) => r.data);

export const emailPatientReport = (id, data) =>
  client.post(`/patients/${id}/report/email`, data).then((r) => r.data);

export const bulkCreateSchedule = (id, data) =>
  client.post(`/patients/${id}/schedule/bulk`, data).then((r) => r.data);
export const updateSchedule = (patientId, scheduleId, data) =>
  client.patch(`/patients/${patientId}/schedule/${scheduleId}`, data).then((r) => r.data);
export const deleteSchedule = (patientId, scheduleId) =>
  client.delete(`/patients/${patientId}/schedule/${scheduleId}`).then((r) => r.data);
