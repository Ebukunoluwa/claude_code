import client from "./client";

export const createProbeCall = (data) =>
  client.post("/probe-calls", data).then((r) => r.data);

export const getPatientProbeCalls = (patientId) =>
  client.get(`/patients/${patientId}/probe-calls`).then((r) => r.data);

export const getProbeCall = (probeCallId) =>
  client.get(`/probe-calls/${probeCallId}`).then((r) => r.data);
