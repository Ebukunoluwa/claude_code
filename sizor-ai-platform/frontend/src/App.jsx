import { Routes, Route, Navigate } from "react-router-dom";
import { getToken } from "./api/auth";
import LoginPage         from "./pages/LoginPage";
import LandingPage       from "./pages/LandingPage";
import DashboardPage     from "./pages/DashboardPage";
import PatientPage       from "./pages/PatientPage";
import PatientDetailPage from "./pages/PatientDetailPage";
import AlertsPage        from "./pages/AlertsPage";
import SchedulerPage     from "./pages/SchedulerPage";
import AnalyticsPage     from "./pages/AnalyticsPage";

function RequireAuth({ children }) {
  return getToken() ? children : <Navigate to="/login" replace />;
}

function Guard({ element }) {
  return <RequireAuth>{element}</RequireAuth>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login"   element={<LoginPage />} />
      <Route path="/landing" element={<LandingPage />} />

      {/* Protected routes */}
      <Route path="/dashboard"      element={<Guard element={<DashboardPage />}     />} />
      <Route path="/patients"       element={<Guard element={<PatientPage />}       />} />
      <Route path="/patients/:id"   element={<Guard element={<PatientDetailPage />} />} />
      <Route path="/alerts"         element={<Guard element={<AlertsPage />}        />} />
      <Route path="/scheduler"      element={<Guard element={<SchedulerPage />}     />} />
      <Route path="/analytics"      element={<Guard element={<AnalyticsPage />}     />} />

      {/* Default redirect */}
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
