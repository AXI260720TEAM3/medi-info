import { Route, Routes } from 'react-router'
import DrugSearch from './pages/DrugSearch'
import DrugDetail from './pages/DrugDetail'

function App(){
  return (
    <Routes>
      <Route path="/drugs" element={<DrugSearch />} />
      <Route path="/drugs/:itemSeq" element={<DrugDetail />} />
    </Routes>
  )
}
export default App