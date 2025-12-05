# 🧾 TableLabelingV2.0

**TableLabeling** is a graphical tool for creating and editing table annotations in images, developed with **Python** and **PyQt5**.
The application helps users easily define table structures, supporting tasks such as training table structure recognition models.

## 🛠️ Installation and Run

You can install and run the application with the following steps:

1. **Download the source code**

   * Clone:

     ```bash
     git clone https://github.com/your_username/TableLabeling.git
     ```
   * Or download the `.zip` file from GitHub and extract it.

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. Download model files

The tool works with TATR-based models (Table Transformer) for automatic table structure detection.
The application expects the model files to be located inside the model/ directory.

Please download your TATR model file separately (e.g., TATR-v1.1-Fin.pth, TATR-SciTSR.pth, etc.) and place it in the model/ folder as shown below:

project_root/
├── main.py
├── table_editor.py
├── auto_labeling.py
├── model/
│   └── your_tatr_model.pth

4. **Run the application**

   ```bash
   python main.py
   ```

## 📌 Usage Guide

### **1. Select folders**

After opening the application:

- Go to **File → Select image folder**  
  → Choose a folder containing images (`.png`, `.jpg`, `.jpeg`, `.bmp`).

- Go to **File → Select label folder**  
  → Choose the folder where XML annotations will be saved.

The left panel will display a list of images with status indicators:

- ❌ **Missing label** – No annotation found  
- ⚠️ **Unchecked label** – Annotation exists but not yet verified  
- ✅ **Checked (saved)** – Annotation has been saved and confirmed


### **2. Viewing and navigating images**

- Click any image in the list to load it.  
- Use the **mouse wheel** to zoom in/out.  
- **Click and drag** to pan around the image.  
- The viewer automatically **fits** the table editor when resized.


### **3. Creating and editing table structure labels**

To manually create table labels:

1. Click **Create table label** in the right panel.  
2. Enter the number of **rows** and **columns**.  
3. A grid will appear on top of the image.

You can then:

- Select **cells, rows, or columns**
- **Merge / Unmerge** cells
- Drag borders to adjust cell sizes
- View updated cell details in the cell list on the right panel


### **4. Auto-generate table labels using TATR**

The application can automatically generate table annotations using TATR-based models.

#### **Option A — Auto-create for the current image**

- Click **Auto Create table label**  
  
#### **Option B — Auto-create for all images in the folder**

- Go to **Tool → Auto Create all table labels**  

The dialog will automatically close when processing is complete.

## 📂 Project Structure

```
TableLabeling/
├── main.py
├── table_editor.py
├── auto_labeling.py
├── model/
│   └── <your_model_files>.pth
├── requirements.txt
├── README.md
```


## 🤝 Contribution

Pull requests and improvements are welcome!
Please open an issue before submitting major changes.


## 📄 License

