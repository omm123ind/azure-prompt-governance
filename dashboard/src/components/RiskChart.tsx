import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend
} from "recharts";

interface Props {
  high: number;
  medium: number;
  low: number;
}

const COLORS = [
  "#ef4444",
  "#f59e0b",
  "#22c55e"
];

export default function RiskChart({
  high,
  medium,
  low
}: Props) {

  const data = [
    {
      name: "High",
      value: high
    },
    {
      name: "Medium",
      value: medium
    },
    {
      name: "Low",
      value: low
    }
  ];

  return (
    <ResponsiveContainer width="100%" height={320}>

      <PieChart>

        <Pie
          data={data}
          dataKey="value"
          nameKey="name"
          outerRadius={110}
          label
        >

          {data.map((_, index) => (
            <Cell
              key={index}
              fill={COLORS[index]}
            />
          ))}

        </Pie>

        <Legend />

        <Tooltip />

      </PieChart>

    </ResponsiveContainer>
  );

}