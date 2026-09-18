import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Landing from './pages/Landing'
import Upload from './pages/Upload'
import Generate from './pages/Generate'
import Dashboard from './pages/Dashboard'
import Validation from './pages/Validation'
import Privacy from './pages/Privacy'
import SyntheticData from './pages/SyntheticData'
import Reports from './pages/Reports'

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/"           element={<Landing />} />
        <Route path="/upload"     element={<Upload />} />
        <Route path="/generate"   element={<Generate />} />
        <Route path="/dashboard"  element={<Dashboard />} />
        <Route path="/validation" element={<Validation />} />
        <Route path="/privacy"    element={<Privacy />} />
        <Route path="/synthetic"  element={<SyntheticData />} />
        <Route path="/reports"    element={<Reports />} />
      </Routes>
    </Layout>
  )
}
