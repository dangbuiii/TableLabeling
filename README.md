# About TableLabeling

**TableLabeling** is a graphical tool developed with **Python** and **PyQt5** for creating and editing table annotations in images. The application helps users easily define table structures, making it particularly useful for training table structure recognition models. Notably, it features specialized capabilities to handle challenging layouts, such as **borderless tables** and complex **merged cells**.

<img width="1919" height="1004" alt="tool" src="https://github.com/user-attachments/assets/cd53b1f3-9565-4b22-a8ed-2ab0c1ed441e" />

## Recent Update

- 2026.07: Our public VietFinTab dataset includes over 10,000 labeled table images from the financial reports of 13 Vietnamese companies. All data were annotated using the TableLabeling tool.


   VietFinTab dataset: https://huggingface.co/datasets/VietFinTabGroup/VietFinTab


## Installation

You can install and run the application with the following steps:


1. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

2. **Download model files**

The tool works with TATR-based models (Table Transformer) for automatic table structure detection.
The application expects the model files to be located inside the `model/` directory.

Please download your TATR model file separately (e.g., TATR-v1.1-Fin.pth, TATR-SciTSR.pth, etc.) and place it in the model/ folder as shown below:

```
project_root/
├── main.py
├── table_editor.py
├── auto_labeling.py
├── model/
│   └── your_tatr_model.pth
```

3. **Run the application**

   ```bash
   python main.py
   ```

## Usage

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

![demo](https://github.com/user-attachments/assets/a6651a10-8442-4f6c-a28e-b0dc3a3bb641)


### **4. Auto-generate table labels using TATR**

The application can automatically generate table annotations using TATR-based models.

![demo](./gif/Recording%202026-08-16%20111442.gif)

*Note: The examples provided use our fine-tuned model rather than the original TATR model.*

#### **Option A — Auto-create for the current image**

- Click **Auto Create table label**  
  
#### **Option B — Auto-create for all images in the folder**

- Go to **Tool → Auto Create all table labels**  

The dialog will automatically close when processing is complete.


## Contribution

Pull requests and improvements are welcome!
Please send a pull request.


## License
[LICENSE](./LICENSE.txt)


Citation: Hong Quan Pham, Hai Dang Bui. TableLabeling. Git code (2026). https://github.com/dangbuiii/TableLabeling
