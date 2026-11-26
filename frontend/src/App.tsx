import { Navigate, Route, Routes } from 'react-router-dom'
import { AppLayout } from './components/AppLayout'
import { useAuth } from './auth/AuthContext'
import { RequireAuth } from './routes/RequireAuth'
import { RequireRole } from './routes/RequireRole'
import { defaultRouteForRole } from './routes/roles'
import { LoginPage } from './pages/LoginPage'
import { DashboardPage } from './pages/DashboardPage'
import { NewAnalysisPage } from './pages/NewAnalysisPage'
import { QueuePage } from './pages/QueuePage'
import { CaseReportPage } from './pages/CaseReportPage'
import { PatientsPage } from './pages/PatientsPage'
import { ModelPerformancePage } from './pages/ModelPerformancePage'
import { SettingsPage } from './pages/SettingsPage'

// Routes match design/README.md's file-to-route map exactly (see
// docs/design.md#design-file-map). Role visibility matches the permission
// matrix in docs/requirements.md#user-roles — enforced here AND by the
// backend (backend/app/deps.py), never only on the frontend.
export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route element={<RequireAuth />}>
        <Route element={<AppLayout />}>
          <Route element={<RequireRole roles={['doctor']} />}>
            <Route path="/" element={<DashboardPage />} />
          </Route>

          <Route element={<RequireRole roles={['doctor', 'radiographer']} />}>
            <Route path="/analysis/new" element={<NewAnalysisPage />} />
            <Route path="/queue" element={<QueuePage />} />
            <Route path="/cases/:id" element={<CaseReportPage />} />
            <Route path="/patients" element={<PatientsPage />} />
          </Route>

          <Route element={<RequireRole roles={['doctor', 'admin']} />}>
            <Route path="/model" element={<ModelPerformancePage />} />
          </Route>

          <Route element={<RequireRole roles={['admin']} />}>
            <Route path="/settings" element={<SettingsPage />} />
          </Route>
        </Route>
      </Route>

      <Route path="*" element={<NotFoundRedirect />} />
    </Routes>
  )
}

function NotFoundRedirect() {
  const { user } = useAuth()
  return <Navigate to={user ? defaultRouteForRole(user.role) : '/login'} replace />
}
