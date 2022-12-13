import React, { useEffect, useState } from "react";
import Navbar from "../../component/Navbar/Navbar";
import ImageShow from "../../component/MainImage/ImageShow";
import { clothesType, reqScrappedList } from "../../apis/get";
const ScrappedItem = () => {
  const [data, setData] = useState<any>([]);
  const setScrap = async () => {
    const username = localStorage.getItem("username");
    const response = await reqScrappedList(username);
    setData(response);
  };
  useEffect(() => {
    setScrap().catch((err: any) => {
      alert(err.message);
    });
  }, []);
  return (
    <div>
      <Navbar />
      <div>this is ScrappedItem</div>
      <div>
        {data.map((d: clothesType) => (
          <ImageShow
            key={d.id}
            id={d.id}
            src={d.photo}
            name={d.name}
            URL={d.URL}
            size={d.named_size}
            WholeData={data}
          />
        ))}
      </div>
    </div>
  );
};
export default ScrappedItem;
