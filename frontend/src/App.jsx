import { Navigate, Route, Routes } from 'react-router'
import Layout from './components/Layout'
import ErrorMessage from './components/ErrorMessage'
import DrugSearch from './pages/DrugSearch'
import DrugDetail from './pages/DrugDetail'

function App(){
  return (
    <Routes>
      {/* Layout 안의 화면들은 상단 메뉴 · 아래 안내가 자동으로 붙어요 */}
      <Route element={<Layout />}>
        <Route path="/" element={<Navigate to="/drugs" replace />} />
        <Route path="/drugs" element={<DrugSearch />} />
        <Route path="/drugs/:itemSeq" element={<DrugDetail />} />
        <Route path="*" element={<ErrorMessage message="없는 페이지예요. 주소를 확인해 주세요." />} />
      </Route>
    </Routes>
  )
}
export default App
