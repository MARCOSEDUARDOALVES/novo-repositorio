
import { useState } from 'react'
import { Button } from '@/components/ui/button.jsx'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card.jsx'
import { Input } from '@/components/ui/input.jsx'
import { Label } from '@/components/ui/label.jsx'
import { Sparkles, Calendar, Clock, MapPin, Loader2, Star, TrendingUp, Users } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import './App.css'

function App() {
  const [formData, setFormData] = useState({
    name: '',
    birth_date: '',
    birth_time: '',
    latitude: '',
    longitude: ''
  })
  
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState(null)
  const [error, setError] = useState(null)

  const handleInputChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value
    }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setResults(null)

    try {
      const dataToSend = { ...formData };
      if (dataToSend.birth_time && dataToSend.birth_time.length === 5) { // HH:MM
        dataToSend.birth_time += ":00"; // Adiciona segundos
      }

      const response = await fetch('/api/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(dataToSend)
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.error || 'Erro ao processar a análise')
      }

      const data = await response.json()
      setResults(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const COLORS = ['#8b5cf6', '#06b6d4', '#10b981', '#f59e0b', '#ef4444']

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-purple-50 to-pink-50 dark:from-gray-900 dark:via-purple-900 dark:to-indigo-900">
      <div className="container mx-auto px-4 py-8 max-w-6xl">
        {/* Header */}
        <div className="text-center mb-12 animate-fade-in">
          <div className="flex items-center justify-center mb-4">
            <Sparkles className="w-12 h-12 text-purple-600 dark:text-purple-400 mr-3" />
            <h1 className="text-5xl font-bold bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">
              Astro Profissões
            </h1>
          </div>
          <p className="text-lg text-gray-600 dark:text-gray-300">
            Descubra sua vocação profissional através da astrologia e inteligência artificial
          </p>
        </div>

        {/* Form Card */}
        {!results && (
          <Card className="mb-8 shadow-2xl animate-slide-up">
            <CardHeader>
              <CardTitle className="text-2xl">Dados de Nascimento</CardTitle>
              <CardDescription>
                Preencha suas informações para gerar sua análise astrológica personalizada
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <Label htmlFor="name">Nome Completo</Label>
                    <Input
                      id="name"
                      name="name"
                      value={formData.name}
                      onChange={handleInputChange}
                      placeholder="Seu nome"
                      required
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="birth_date" className="flex items-center gap-2">
                      <Calendar className="w-4 h-4" />
                      Data de Nascimento
                    </Label>
                    <Input
                      id="birth_date"
                      name="birth_date"
                      type="date"
                      value={formData.birth_date}
                      onChange={handleInputChange}
                      required
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="birth_time" className="flex items-center gap-2">
                      <Clock className="w-4 h-4" />
                      Hora de Nascimento
                    </Label>
                    <Input
                      id="birth_time"
                      name="birth_time"
                      type="time"
                      value={formData.birth_time}
                      onChange={handleInputChange}
                      required
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="latitude" className="flex items-center gap-2">
                      <MapPin className="w-4 h-4" />
                      Latitude
                    </Label>
                    <Input
                      id="latitude"
                      name="latitude"
                      type="number"
                      step="any"
                      value={formData.latitude}
                      onChange={handleInputChange}
                      placeholder="-23.5505"
                      required
                    />
                  </div>

                  <div className="space-y-2 md:col-span-2">
                    <Label htmlFor="longitude">Longitude</Label>
                    <Input
                      id="longitude"
                      name="longitude"
                      type="number"
                      step="any"
                      value={formData.longitude}
                      onChange={handleInputChange}
                      placeholder="-46.6333"
                      required
                    />
                  </div>
                </div>

                {error && (
                  <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-800 dark:text-red-200">
                    {error}
                  </div>
                )}

                <Button 
                  type="submit" 
                  className="w-full h-12 text-lg" 
                  disabled={loading}
                >
                  {loading ? (
                    <>
                      <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                      Analisando seu mapa astral...
                    </>
                  ) : (
                    <>
                      <Sparkles className="mr-2 h-5 w-5" />
                      Descobrir Minha Vocação
                    </>
                  )}
                </Button>
              </form>
            </CardContent>
          </Card>
        )}

        {/* Results Section */}
        {results && (
          <div className="space-y-8 animate-fade-in">
            {/* Predictions Card */}
            <Card className="shadow-2xl">
              <CardHeader>
                <CardTitle className="text-2xl flex items-center gap-2">
                  <TrendingUp className="w-6 h-6 text-purple-600" />
                  Previsões de Profissões
                </CardTitle>
                <CardDescription>
                  Baseado nas características do seu mapa astral
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4 mb-6">
                  {results.predictions.map((pred, index) => (
                    <div 
                      key={index}
                      className="flex items-center justify-between p-4 rounded-lg bg-gradient-to-r from-purple-50 to-pink-50 dark:from-purple-900/20 dark:to-pink-900/20 border border-purple-200 dark:border-purple-800 hover:scale-[1.02] transition-transform"
                    >
                      <div className="flex items-center gap-3">
                        <div className={`w-10 h-10 rounded-full flex items-center justify-center text-white font-bold ${
                          index === 0 ? 'bg-gradient-to-r from-yellow-400 to-orange-500' :
                          index === 1 ? 'bg-gradient-to-r from-gray-300 to-gray-400' :
                          index === 2 ? 'bg-gradient-to-r from-orange-400 to-orange-600' :
                          'bg-gradient-to-r from-purple-400 to-pink-500'
                        }`}>
                          {index + 1}
                        </div>
                        <div>
                          <p className="font-semibold text-lg">{pred.profession}</p>
                          <p className="text-sm text-gray-600 dark:text-gray-400">
                            Confiança: {pred.confidence === 'high' ? 'Alta' : pred.confidence === 'medium' ? 'Média' : 'Baixa'}
                          </p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="text-2xl font-bold text-purple-600 dark:text-purple-400">
                          {(pred.probability * 100).toFixed(1)}%
                        </p>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="h-80">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={results.predictions}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis 
                        dataKey="profession" 
                        angle={-45}
                        textAnchor="end"
                        height={100}
                        fontSize={12}
                      />
                      <YAxis 
                        label={{ value: 'Probabilidade (%)', angle: -90, position: 'insideLeft' }}
                      />
                      <Tooltip 
                        formatter={(value) => `${(value * 100).toFixed(1)}%`}
                        labelStyle={{ color: '#000' }}
                      />
                      <Bar dataKey="probability" radius={[8, 8, 0, 0]}>
                        {results.predictions.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            {/* Interpretation Card */}
            <Card className="shadow-2xl">
              <CardHeader>
                <CardTitle className="text-2xl flex items-center gap-2">
                  <Star className="w-6 h-6 text-yellow-500" />
                  Interpretação Astrológica
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="p-4 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 border border-blue-200 dark:border-blue-800">
                    <p className="text-lg leading-relaxed">{results.interpretation.summary}</p>
                  </div>
                  
                  <div>
                    <h3 className="font-semibold text-lg mb-3">Fatores Chave:</h3>
                    <ul className="space-y-2">
                      {results.interpretation.key_factors.map((factor, index) => (
                        <li key={index} className="flex items-start gap-2">
                          <Star className="w-5 h-5 text-yellow-500 mt-0.5 flex-shrink-0" />
                          <span className="text-gray-700 dark:text-gray-300">{factor}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Similar Profiles Card */}
            <Card className="shadow-2xl">
              <CardHeader>
                <CardTitle className="text-2xl flex items-center gap-2">
                  <Users className="w-6 h-6 text-green-600" />
                  Perfis Similares
                </CardTitle>
                <CardDescription>
                  Personalidades famosas com mapas astrais semelhantes ao seu
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {results.similar_profiles.map((profile, index) => (
                    <div 
                      key={index}
                      className="p-4 rounded-lg bg-gradient-to-br from-green-50 to-teal-50 dark:from-green-900/20 dark:to-teal-900/20 border border-green-200 dark:border-green-800 hover:scale-105 transition-transform"
                    >
                      <h4 className="font-semibold text-lg mb-1">{profile.name}</h4>
                      <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">{profile.profession}</p>
                      <div className="flex items-center gap-2">
                        <div className="flex-1 bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                          <div 
                            className="bg-gradient-to-r from-green-500 to-teal-500 h-2 rounded-full"
                            style={{ width: `${profile.similarity * 100}%` }}
                          ></div>
                        </div>
                        <span className="text-sm font-semibold text-green-600 dark:text-green-400">
                          {(profile.similarity * 100).toFixed(0)}%
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* New Analysis Button */}
            <div className="text-center">
              <Button 
                onClick={() => {
                  setResults(null)
                  setFormData({
                    name: '',
                    birth_date: '',
                    birth_time: '',
                    latitude: '',
                    longitude: ''
                  })
                }}
                className="h-12 px-8 text-lg"
              >
                Nova Análise
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default App


